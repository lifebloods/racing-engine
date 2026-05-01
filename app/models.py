from datetime import datetime
from app import db

class Trainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    entries = db.relationship("RaceEntry", back_populates="trainer")

class Jockey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    style = db.Column(db.String(64), nullable=True)
    entries = db.relationship("RaceEntry", back_populates="jockey")

class Pedigree(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sire = db.Column(db.String(128), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    horses = db.relationship("Horse", back_populates="pedigree")

class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    location = db.Column(db.String(128), nullable=True)
    entries = db.relationship("RaceEntry", back_populates="track")

class Race(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    race_date = db.Column(db.Date, nullable=False)
    race_name = db.Column(db.String(256), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey("track.id"), nullable=False)
    grade = db.Column(db.String(64), nullable=True)
    distance = db.Column(db.Integer, nullable=True)
    going = db.Column(db.String(64), nullable=True)
    class_level = db.Column(db.String(64), nullable=True)
    race_category = db.Column(db.String(64), nullable=True)  # e.g., "Thoroughbred", "Harness", "Greyhound"
    race_number = db.Column(db.Integer, nullable=True)
    meeting_code = db.Column(db.String(32), nullable=True)  # TAB meeting code
    entries = db.relationship("RaceEntry", back_populates="race")
    track = db.relationship("Track")

class Horse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gelded = db.Column(db.Boolean, default=False)
    debut = db.Column(db.Boolean, default=False)
    style = db.Column(db.String(64), nullable=True)
    pedigree_id = db.Column(db.Integer, db.ForeignKey("pedigree.id"), nullable=True)
    pedigree = db.relationship("Pedigree", back_populates="horses")
    entries = db.relationship("RaceEntry", back_populates="horse")

class RaceEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"), nullable=False)
    horse_id = db.Column(db.Integer, db.ForeignKey("horse.id"), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey("trainer.id"), nullable=True)
    jockey_id = db.Column(db.Integer, db.ForeignKey("jockey.id"), nullable=True)
    track_id = db.Column(db.Integer, db.ForeignKey("track.id"), nullable=True)
    barrier = db.Column(db.Integer, nullable=True)
    current_odds = db.Column(db.Float, nullable=True)
    opening_odds = db.Column(db.Float, nullable=True)
    tab_odds = db.Column(db.Float, nullable=True)  # Live TAB odds
    finish_position = db.Column(db.Integer, nullable=True)
    blocked = db.Column(db.Boolean, default=False)
    checked = db.Column(db.Boolean, default=False)
    wide = db.Column(db.Boolean, default=False)
    speed_rating = db.Column(db.Float, nullable=True)
    benchmark_change = db.Column(db.Integer, nullable=True)
    blinkers_first_time = db.Column(db.Boolean, default=False)
    tongue_tie_first_time = db.Column(db.Boolean, default=False)
    apprentice_claim = db.Column(db.Float, nullable=True)
    barrier_behavior = db.Column(db.String(128), nullable=True)
    travel_distance = db.Column(db.Integer, nullable=True)
    market_swing = db.Column(db.Float, nullable=True)
    is_second_up = db.Column(db.Boolean, default=False)
    last_start_grade = db.Column(db.String(64), nullable=True)
    current_score = db.Column(db.Float, default=10.0)
    arrow = db.Column(db.String(16), nullable=True)
    is_scratched = db.Column(db.Boolean, default=False)  # Scratch status
    scratched_at = db.Column(db.DateTime, nullable=True)  # When scratched
    tab_runner_number = db.Column(db.Integer, nullable=True)  # TAB runner ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    race = db.relationship("Race", back_populates="entries")
    horse = db.relationship("Horse", back_populates="entries")
    trainer = db.relationship("Trainer", back_populates="entries")
    jockey = db.relationship("Jockey", back_populates="entries")
    track = db.relationship("Track", back_populates="entries")

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    race_entry_id = db.Column(db.Integer, db.ForeignKey("race_entry.id"), nullable=False)
    stake = db.Column(db.Float, nullable=False)
    bet_type = db.Column(db.String(64), nullable=False)  # Win, Place, Exacta, Trifecta, Quinella, etc.
    market_odds = db.Column(db.Float, nullable=False)
    result = db.Column(db.String(64), nullable=True)  # Won, Lost, Placed, etc.
    profit_loss = db.Column(db.Float, nullable=True)
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    race_entry = db.relationship("RaceEntry")


class BonusBet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bet_name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    stake = db.Column(db.Float, nullable=False)
    bet_type = db.Column(db.String(64), nullable=False)  # Multi, Parlay, etc.
    selections = db.Column(db.JSON, nullable=False)  # List of race_entry_ids
    odds_combined = db.Column(db.Float, nullable=False)
    result = db.Column(db.String(64), nullable=True)  # Won, Lost, Part Win, etc.
    profit_loss = db.Column(db.Float, nullable=True)
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    settled_at = db.Column(db.DateTime, nullable=True)
