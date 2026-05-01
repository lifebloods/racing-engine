"""
TAB (The Sportsbet) scraper for live odds and race information.
TAB is the primary betting platform in Australia.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import re
from app import db
from app.models import RaceEntry, Race, Horse, Trainer, Jockey, Track
import json

TAB_BASE_URL = "https://www.tab.com.au"
TAB_API_URL = "https://api.tab.com.au"

def safe_get(url, headers=None, timeout=15):
    """Safe GET request with user agent"""
    headers = headers or {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def fetch_tab_racing_meetings(race_date=None):
    """Fetch available racing meetings from TAB for a given date"""
    if race_date is None:
        race_date = date.today()
    
    # TAB racing page format: YYYYMMDD
    date_str = race_date.strftime("%Y%m%d")
    url = f"{TAB_BASE_URL}/Racing/{date_str}"
    
    response = safe_get(url)
    if not response:
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    meetings = []
    
    # Parse meeting divs
    meeting_links = soup.select("div.meeting a.meeting-link")
    for link in meeting_links:
        meeting_code = link.get("data-meeting-code")
        meeting_name = link.get_text(strip=True)
        if meeting_code and meeting_name:
            meetings.append({
                "code": meeting_code,
                "name": meeting_name,
                "url": link.get("href")
            })
    
    return meetings


def fetch_race_details(meeting_code, race_number):
    """Fetch detailed race info and odds from TAB"""
    url = f"{TAB_BASE_URL}/Racing/Race/{meeting_code}/{race_number}"
    
    response = safe_get(url)
    if not response:
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    race_info = {
        "runners": [],
        "race_conditions": {}
    }
    
    # Extract race conditions (going, distance, class, etc.)
    conditions_text = soup.select_one("div.race-conditions")
    if conditions_text:
        text = conditions_text.get_text()
        # Parse distance
        distance_match = re.search(r"(\d+)m", text)
        if distance_match:
            race_info["race_conditions"]["distance"] = int(distance_match.group(1))
        
        # Parse going/track condition
        going_match = re.search(r"(Good|Soft|Heavy|Firm|Good3|Soft4|Soft5|Heavy6|Heavy7|Heavy8|Good4|Good5)", text)
        if going_match:
            race_info["race_conditions"]["going"] = going_match.group(1)
        
        # Parse class
        class_match = re.search(r"Class\s+([A-Za-z0-9\s]+?)(?:\s+|$)", text)
        if class_match:
            race_info["race_conditions"]["class"] = class_match.group(1).strip()
    
    # Extract runners with odds
    runner_rows = soup.select("tr.runner-row")
    for row in runner_rows:
        runner_num = row.select_one("td.runner-num")
        horse_name = row.select_one("td.horse-name a")
        current_odds = row.select_one("td.current-odds")
        scratched = row.select_one("span.scratched")
        
        if runner_num and horse_name:
            runner_data = {
                "number": runner_num.get_text(strip=True),
                "horse_name": horse_name.get_text(strip=True),
                "odds": float(current_odds.get_text(strip=True).replace("$", "")) if current_odds else None,
                "is_scratched": scratched is not None
            }
            race_info["runners"].append(runner_data)
    
    return race_info


def update_race_entry_odds(meeting_code, race_number, race_entry_id):
    """Update a specific race entry with latest TAB odds"""
    try:
        race_details = fetch_race_details(meeting_code, race_number)
        if not race_details:
            return False
        
        entry = RaceEntry.query.get(race_entry_id)
        if not entry:
            return False
        
        # Find matching runner
        for runner in race_details["runners"]:
            if runner["horse_name"].lower() == entry.horse.name.lower():
                # Update odds
                entry.tab_odds = runner.get("odds")
                
                # Update scratch status
                if runner["is_scratched"] and not entry.is_scratched:
                    entry.is_scratched = True
                    entry.scratched_at = datetime.utcnow()
                
                db.session.commit()
                return True
        
        return False
    except Exception as e:
        print(f"Error updating odds for entry {race_entry_id}: {e}")
        return False


def update_all_race_odds():
    """Fetch and update odds for all upcoming races"""
    try:
        # Get all non-scratched, upcoming race entries
        upcoming_entries = RaceEntry.query.filter(
            RaceEntry.is_scratched == False,
            RaceEntry.finish_position.is_(None)  # Not finished yet
        ).all()
        
        updated_count = 0
        for entry in upcoming_entries:
            if entry.race and entry.race.meeting_code:
                if update_race_entry_odds(
                    entry.race.meeting_code,
                    entry.race.race_number,
                    entry.id
                ):
                    updated_count += 1
        
        return updated_count
    except Exception as e:
        print(f"Error updating all race odds: {e}")
        return 0


def detect_scratchings():
    """Detect any scratchings that occurred"""
    try:
        # Get all non-scratched, upcoming race entries
        active_entries = RaceEntry.query.filter(
            RaceEntry.is_scratched == False,
            RaceEntry.finish_position.is_(None)
        ).all()
        
        scratched_count = 0
        for entry in active_entries:
            if entry.race and entry.race.meeting_code:
                race_details = fetch_race_details(
                    entry.race.meeting_code,
                    entry.race.race_number
                )
                
                if race_details:
                    for runner in race_details["runners"]:
                        if (runner["horse_name"].lower() == entry.horse.name.lower() and 
                            runner["is_scratched"] and not entry.is_scratched):
                            
                            entry.is_scratched = True
                            entry.scratched_at = datetime.utcnow()
                            scratched_count += 1
        
        if scratched_count > 0:
            db.session.commit()
        
        return scratched_count
    except Exception as e:
        print(f"Error detecting scratchings: {e}")
        return 0


def categorize_race(race_name, meeting_code):
    """Determine race category based on meeting code and race name"""
    race_name_lower = race_name.lower()
    meeting_code_lower = meeting_code.lower() if meeting_code else ""
    
    # Check for harness racing indicators
    if "trotting" in race_name_lower or "harness" in meeting_code_lower or "hrnz" in meeting_code_lower:
        return "Harness"
    
    # Check for greyhound racing indicators
    if "greyhound" in race_name_lower or "grey" in meeting_code_lower:
        return "Greyhound"
    
    # Default to thoroughbred
    return "Thoroughbred"
