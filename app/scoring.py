from app.models import RaceEntry

ELITE_COMBOS = {
    ("Waller", "J-Mac"): 10,
    ("Dunn", "Looker"): 10,
}
TRACK_SNIPERS = {
    ("Aaron Bullock", "Scone"): 5,
}
MUDLARK_SIRES = {"Snitzel", "Dundeel"}
EARLY_DEVELOPERS = {"Exceed and Excel"}

STYLE_ALIGNMENT = {
    ("front-runner", "front-runner"): 6,
    ("stalker", "stalker"): 4,
    ("closer", "closer"): 5,
    ("front-runner", "stalker"): 2,
    ("stalker", "closer"): 1,
}

WET_GRADE_KEYWORDS = {"soft", "heavy", "soft7", "heavy8", "heavy10", "heavy9", "heavy11"}
BARRIER_RISK_TERMS = {"slow starter", "barrier rogue", "bad barrier", "hung", "jumped awkwardly"}
POWER_SHIFT_CLASSES = {"metro": {"provincial", "country"}}
BASE_SCORE = 10


def normalize_text(value):
    if value is None:
        return None
    return value.strip().lower()


def is_wet_going(going):
    return normalize_text(going) in WET_GRADE_KEYWORDS


def elite_combo_bonus(entry: RaceEntry) -> int:
    if entry.trainer and entry.jockey:
        return ELITE_COMBOS.get((entry.trainer.name, entry.jockey.name), 0)
    return 0


def track_sniper_bonus(entry: RaceEntry) -> int:
    if entry.jockey and entry.track:
        return TRACK_SNIPERS.get((entry.jockey.name, entry.track.name), 0)
    return 0


def style_alignment_bonus(entry: RaceEntry) -> int:
    if entry.horse and entry.horse.style and entry.jockey and entry.jockey.style:
        return STYLE_ALIGNMENT.get((entry.horse.style, entry.jockey.style), 0)
    return 0


def pedigree_bonus(entry: RaceEntry) -> int:
    if not entry.horse or not entry.horse.pedigree:
        return 0

    pedigree = entry.horse.pedigree
    score = 0
    if pedigree.verified and pedigree.sire in MUDLARK_SIRES and entry.race and is_wet_going(entry.race.going):
        score += 7
    if pedigree.verified and entry.horse.age == 2 and entry.horse.debut and pedigree.sire in EARLY_DEVELOPERS:
        score += 4
    if pedigree.verified and entry.apprentice_claim and entry.apprentice_claim >= 3 and entry.race and is_wet_going(entry.race.going):
        score += 6
    return score


def mechanical_bonus(entry: RaceEntry) -> int:
    score = 0
    if entry.horse and entry.horse.gelded:
        score += 8
    if entry.blinkers_first_time:
        score += 6
    if entry.tongue_tie_first_time:
        score += 4
    if entry.barrier_behavior and normalize_text(entry.barrier_behavior) in BARRIER_RISK_TERMS:
        score -= 3
    return score


def travel_bonus(entry: RaceEntry) -> int:
    if entry.travel_distance and entry.travel_distance >= 400:
        return 5
    return 0


def form_bonus(entry: RaceEntry) -> int:
    score = 0
    if entry.blocked or entry.checked or entry.wide:
        score += 5
    if entry.benchmark_change is not None:
        if entry.benchmark_change > 0:
            score += min(entry.benchmark_change * 2, 8)
        elif entry.benchmark_change < 0:
            score -= min(abs(entry.benchmark_change) * 2, 6)
    if entry.is_second_up and entry.speed_rating and entry.speed_rating >= 90 and entry.benchmark_change and entry.benchmark_change >= 8:
        score -= 5
    if entry.last_start_grade and entry.race and entry.race.class_level:
        if normalize_text(entry.last_start_grade) == "metro" and normalize_text(entry.race.class_level) in POWER_SHIFT_CLASSES.get("metro", set()):
            score += 4
    return score


def speed_bonus(entry: RaceEntry) -> float:
    if entry.speed_rating is None:
        return 0
    return (entry.speed_rating - 50) * 0.1


def market_bonus(entry: RaceEntry) -> int:
    if entry.opening_odds and entry.current_odds and entry.opening_odds > 0:
        swing = entry.opening_odds - entry.current_odds
        if swing / entry.opening_odds >= 0.2:
            entry.market_swing = swing
            return 5
    return 0


def determine_arrow(entry: RaceEntry) -> str:
    if entry.speed_rating is None:
        return "➡️"
    if entry.benchmark_change and entry.benchmark_change > 4:
        return "⬆️"
    if entry.benchmark_change and entry.benchmark_change < 0:
        return "⬇️"
    if entry.speed_rating >= 88:
        return "⬆️"
    if entry.speed_rating <= 65:
        return "⬇️"
    return "➡️"


def evaluate_entry(entry: RaceEntry) -> float:
    score = BASE_SCORE
    score += elite_combo_bonus(entry)
    score += track_sniper_bonus(entry)
    score += style_alignment_bonus(entry)
    score += travel_bonus(entry)
    score += pedigree_bonus(entry)
    score += mechanical_bonus(entry)
    score += form_bonus(entry)
    score += speed_bonus(entry)
    score += market_bonus(entry)

    entry.current_score = round(score, 1)
    entry.arrow = determine_arrow(entry)
    return entry.current_score


def score_all(entries):
    for entry in entries:
        evaluate_entry(entry)
    return entries
