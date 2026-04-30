# Lethal Engine

A Python Flask application for RacingAustralia data modeling, scoring, and bet tracking. The app is designed to work on desktop and mobile browsers with a simple interface, and it includes a scoring engine for the "Logic Core" metrics you provided.

## Features

- Flask web app with responsive dashboard
- SQLite data storage for race entries and bet history
- Scoring engine with:
  - Elite trainer/jockey combo bonuses
  - Track sniper recognition
  - Genetic and wet-ground bias metrics
  - Gear trigger support (blinkers, tongue tie, gelding)
  - Form trajectory arrow system
  - Market swing detection
- Bet tracker UI for adding and updating wagers
- Scraper skeleton for RacingAustralia data refresh

## Setup

1. Install Python 3.11+ if needed. On Windows, use the official installer from python.org or enable the executable from the Microsoft Store.

2. Create a Python virtual environment:

   ```powershell
   cd C:\Users\Ethan\Desktop\racing-engine
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Run the application:

   ```powershell
   python run.py
   ```

3. Open `http://localhost:5000` in your browser.

## Notes

- The scraper now parses RacingAustralia calendar and meeting form pages to extract real race cards, horses, trainers, jockeys, and race metadata.
- The scoring engine is modular and can be extended with additional metrics and refined weights.
- The app saves data into `data/racing_engine.db`.

## Next steps

- Add real RacingAustralia scraping logic and parsing rules.
- Extend the scoring rules with explicit historical analytics.
- Add bankroll management and staking calculators for Dutching/Kelly.
- Support detailed race cards, performance history, and dynamic edge detection.
