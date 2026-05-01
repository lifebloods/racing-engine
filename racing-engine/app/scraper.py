import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from app import db
from app.models import Track, Race, Horse, Trainer, Jockey, RaceEntry
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://racingaustralia.horse"
CALENDAR_PATH = "/FreeFields/Calendar.aspx"
DEFAULT_STATES = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
MAX_MEETINGS_PER_STATE = 1


def safe_get(url, headers=None, timeout=15):
    headers = headers or {
        "User-Agent": "LethalEngineBot/1.0 (+https://example.com)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_date_from_key(key):
    try:
        date_part = key.split(",")[0]
        return datetime.strptime(date_part, "%Y%b%d").date()
    except (ValueError, IndexError):
        return None


def normalize_text(text):
    if not text:
        return None
    return re.sub(r"\s+", " ", text.strip())


def parse_float(value):
    if not value:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value.replace(",", ""))
    return float(match.group(1)) if match else None


def parse_int(value):
    if not value:
        return None
    match = re.search(r"(\d+)", value.replace(",", ""))
    return int(match.group(1)) if match else None


def parse_weight(value):
    if not value:
        return None
    return parse_float(value)


def parse_track_condition(soup):
    page_text = soup.get_text(" ", strip=True)
    match = re.search(r"Track Condition:\s*([A-Za-z0-9\s]+?)(?:Weather:|Penetrometer:|Track Information:|$)", page_text)
    if match:
        return normalize_text(match.group(1))
    return None


def parse_track_name(soup):
    title_tag = soup.select_one("div.race-venue h2")
    if not title_tag:
        return None
    date_span = title_tag.select_one("span.race-venue-date")
    if date_span:
        date_span.extract()
    return normalize_text(title_tag.get_text(" ", strip=True))


def parse_race_name(title_table):
    if not title_table:
        return None
    title_text = title_table.get_text(" ", strip=True)
    title_text = re.sub(r"Times displayed.*$", "", title_text)
    title_text = re.sub(r"^Race\s*\d+\s*-\s*", "", title_text)
    return normalize_text(title_text)


def parse_race_class(title_table):
    info_row = title_table.find("tr", class_="race-info")
    if not info_row:
        return None
    info_text = normalize_text(info_row.get_text(" ", strip=True))
    if not info_text:
        return None
    if len(info_text) > 64:
        return info_text[:64]
    return info_text


def parse_entries(entries_table):
    entries = []
    if not entries_table:
        return entries
    for row in entries_table.select("tr"):
        if row.find("th"):
            continue
        classes = row.get("class") or []
        if isinstance(classes, list):
            classes = " ".join(classes)
        if "scratched" in classes.lower():
            continue
        cells = row.select("td")
        if len(cells) < 10:
            continue

        horse_cell = cells[2]
        horse_link = horse_cell.find("a")
        horse_name = horse_link.get_text(strip=True) if horse_link else normalize_text(horse_cell.get_text(" ", strip=True))
        horse_code = None
        if horse_link and horse_link.has_attr("href"):
            horse_href = horse_link["href"]
            horse_code = parse_qs(urlparse(horse_href).query).get("horsecode", [None])[0]

        jockey_text = normalize_text(cells[4].get_text(" ", strip=True))
        apprentice_claim = 0.0 if re.search(r"\(a", jockey_text, re.I) else None
        jockey_name = re.sub(r"\s*\(a[^\)]*\)", "", jockey_text, flags=re.I).strip()
        jockey_name = normalize_text(jockey_name)

        entries.append(
            {
                "number": parse_int(cells[0].get_text(strip=True)),
                "last_10": normalize_text(cells[1].get_text(" ", strip=True)),
                "horse_name": horse_name,
                "horse_code": horse_code,
                "trainer": normalize_text(cells[3].get_text(" ", strip=True)),
                "jockey": jockey_name,
                "apprentice_claim": apprentice_claim,
                "barrier": parse_int(cells[5].get_text(strip=True)),
                "weight": parse_weight(cells[6].get_text(strip=True)),
                "probable_weight": parse_weight(cells[7].get_text(strip=True)),
                "penalty": parse_float(cells[8].get_text(strip=True)),
                "hcp_rating": parse_int(cells[9].get_text(strip=True)),
            }
        )
    return entries


def parse_meeting_keys(state="NSW", limit=MAX_MEETINGS_PER_STATE):
    html = safe_get(f"{BASE_URL}{CALENDAR_PATH}?State={state}")
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.race-fields")
    if not table:
        return []

    meetings = []
    for row in table.select("tr"):
        if row.find("th"):
            continue
        cells = row.select("td")
        if len(cells) < 6:
            continue
        form_cell = cells[5]
        form_link = form_cell.find("a")
        if not form_link or "Form.aspx" not in form_link.get("href", ""):
            continue
        href = form_link["href"]
        if not href:
            continue
        parsed = urlparse(href)
        query = parse_qs(parsed.query)
        key = query.get("Key", [None])[0]
        if not key:
            continue
        venue = normalize_text(cells[1].get_text(" ", strip=True))
        meeting_date = parse_date_from_key(key)
        meetings.append({"state": state, "key": key, "venue": venue, "date": meeting_date})
        if len(meetings) >= limit:
            break
    return meetings


def fetch_race_cards(states=None, limit_per_state=MAX_MEETINGS_PER_STATE):
    states = states or DEFAULT_STATES
    meeting_keys = []
    for state in states:
        meeting_keys.extend(parse_meeting_keys(state, limit=limit_per_state))
    unique_meetings = []
    seen = set()
    for meeting in meeting_keys:
        if meeting["key"] in seen:
            continue
        seen.add(meeting["key"])
        unique_meetings.append(meeting)
    races = []
    for meeting in unique_meetings:
        try:
            html = safe_get(f"{BASE_URL}/FreeFields/Form.aspx?Key={meeting['key']}")
            races.extend(parse_form_page(html, meeting))
        except Exception:
            continue
    return races


def parse_form_page(html, meeting):
    soup = BeautifulSoup(html, "html.parser")
    track_name = parse_track_name(soup) or meeting.get("venue")
    going = parse_track_condition(soup)
    race_date = meeting.get("date") or parse_date_from_key(meeting.get("key", "")) or datetime.utcnow().date()

    races = []
    for anchor in soup.find_all("a", attrs={"name": re.compile(r"^Race\d+$")}):
        title_table = anchor.find_next("table", class_="race-title")
        if not title_table:
            continue
        race_name = parse_race_name(title_table)
        class_level = parse_race_class(title_table)
        distance = None
        if race_name:
            distance_match = re.search(r"(\d+)\s*METRES?", race_name, re.I)
            if distance_match:
                distance = int(distance_match.group(1))

        entries_table = title_table.find_next("table", class_="race-strip-fields")
        entries = parse_entries(entries_table)
        races.append(
            {
                "race_name": race_name,
                "track_name": track_name,
                "race_date": race_date,
                "going": going,
                "distance": distance,
                "class_level": class_level,
                "entries": entries,
            }
        )
    return races


def _get_or_create(model, defaults=None, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    instance = model(**kwargs)
    if defaults:
        for key, value in defaults.items():
            setattr(instance, key, value)
    db.session.add(instance)
    db.session.flush()
    return instance


def refresh_race_data(states=None, limit_per_state=MAX_MEETINGS_PER_STATE):
    races = fetch_race_cards(states=states, limit_per_state=limit_per_state)

    for raw_race in races:
        track_name = raw_race.get("track_name") or "Unknown"
        track = _get_or_create(Track, name=track_name)

        race_date = raw_race.get("race_date") or datetime.utcnow().date()
        race_name = raw_race.get("race_name") or "Unknown Race"
        race = Race.query.filter_by(track_id=track.id, race_date=race_date, race_name=race_name).first()
        
        # Import categorization function from tab_scraper
        from app.tab_scraper import categorize_race
        race_category = categorize_race(race_name, track_name)
        
        if not race:
            race = Race(
                race_date=race_date,
                race_name=race_name,
                track_id=track.id,
                going=raw_race.get("going"),
                distance=raw_race.get("distance"),
                class_level=raw_race.get("class_level"),
                race_category=race_category,
                meeting_code=f"{track_name.upper()}-{race_date.strftime('%Y%m%d')}",
            )
            db.session.add(race)
            db.session.flush()
        else:
            race.going = raw_race.get("going") or race.going
            race.distance = raw_race.get("distance") or race.distance
            race.class_level = raw_race.get("class_level") or race.class_level
            race.race_category = race.race_category or race_category
            race.meeting_code = race.meeting_code or f"{track_name.upper()}-{race_date.strftime('%Y%m%d')}"

        for runner in raw_race.get("entries", []):
            horse_name = runner.get("horse_name")
            if not horse_name:
                continue

            trainer_name = runner.get("trainer")
            jockey_name = runner.get("jockey")
            trainer = _get_or_create(Trainer, name=trainer_name) if trainer_name else None
            jockey = _get_or_create(Jockey, name=jockey_name) if jockey_name else None
            if jockey and runner.get("apprentice_claim") is not None:
                jockey.style = jockey.style or "Apprentice"

            horse = Horse.query.filter_by(name=horse_name).first()
            if not horse:
                horse = Horse(name=horse_name)
            horse.age = runner.get("age")
            horse.gelded = runner.get("gelded", False)
            horse.style = horse.style or runner.get("style")
            horse.debut = runner.get("debut", False)
            db.session.add(horse)
            db.session.flush()

            entry = RaceEntry.query.filter_by(race_id=race.id, horse_id=horse.id).first()
            if not entry:
                entry = RaceEntry(race_id=race.id, horse_id=horse.id)
            entry.trainer_id = trainer.id if trainer else None
            entry.jockey_id = jockey.id if jockey else None
            entry.track_id = track.id
            entry.barrier = runner.get("barrier")
            entry.current_odds = runner.get("current_odds")
            entry.opening_odds = runner.get("opening_odds")
            entry.blocked = runner.get("blocked", False)
            entry.checked = runner.get("checked", False)
            entry.wide = runner.get("wide", False)
            entry.speed_rating = runner.get("speed_rating")
            entry.benchmark_change = runner.get("benchmark_change")
            entry.blinkers_first_time = runner.get("blinkers_first_time", False)
            entry.tongue_tie_first_time = runner.get("tongue_tie_first_time", False)
            entry.apprentice_claim = runner.get("apprentice_claim")
            entry.barrier_behavior = runner.get("barrier_behavior")
            entry.travel_distance = runner.get("travel_distance")
            entry.market_swing = runner.get("market_swing")
            entry.is_second_up = runner.get("is_second_up", False)
            entry.last_start_grade = runner.get("last_start_grade")
            db.session.add(entry)
    db.session.commit()
    return True
