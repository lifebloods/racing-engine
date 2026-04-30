# Lethal Engine - PythonAnywhere Deployment Guide

## Setup Steps (Once Account Created):

### 1. **Upload Code to PythonAnywhere**
From your account dashboard:
- Files → Upload files
- Select your project folder or use Git
- Recommended: Use Git for easier updates
  ```
  git clone https://github.com/yourusername/racing-engine.git
  ```

### 2. **Create Web App**
- Web → Add a new web app
- Choose: **Python 3.11** + **Flask**
- WSGI file location: `/home/yourusername/racing-engine/wsgi.py`

### 3. **Install Requirements**
In Bash console:
```bash
cd /home/yourusername/racing-engine
mkvirtualenv --python=/usr/bin/python3.11 lethal-venv
pip install -r requirements.txt
```

### 4. **Configure Web App**
- Source code: `/home/yourusername/racing-engine`
- Working directory: `/home/yourusername/racing-engine`
- WSGI file: `/home/yourusername/racing-engine/wsgi.py`
- Virtualenv: `/home/yourusername/.virtualenvs/lethal-venv`

### 5. **Set Up Database**
In Bash:
```bash
workon lethal-venv
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 6. **Reload Web App**
Dashboard → Web → Reload your app

### 7. **Access Your App**
`https://yourusername.pythonanywhere.com`

---

## Important Notes:

- **Free tier limitations:**
  - Only HTTP (not HTTPS for custom domains)
  - App sleeps after 3 months of inactivity
  - Limited CPU/memory
  - No real-time scraping from external APIs (TAB odds will be delayed)

- **Database persistence:** SQLite works fine on PythonAnywhere
- **File uploads:** Use `/home/yourusername/` for persistent storage

---

## Metrics Deep-Dive TODO:

Once deployed, we'll refine:
1. **Scoring algorithm** — Add more elite combos, track record bonuses
2. **TAB odds integration** — Real-time odds updates
3. **Form analysis** — Better speed/benchmark detection
4. **Market trends** — Odds movement tracking
5. **Backtesting** — Historical win rates by metric
6. **Dashboard analytics** — Win/loss heatmaps by track, trainer, jockey
7. **Prediction accuracy** — Score vs actual results comparison

Ready to deploy? Send me your PythonAnywhere username once account is created! 🚀
