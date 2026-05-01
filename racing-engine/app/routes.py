from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from app import db
from app.models import RaceEntry, Bet, BonusBet, Race
from app.scoring import score_all
from app.scraper import refresh_race_data
from app.tab_scraper import update_all_race_odds, detect_scratchings
from datetime import datetime

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    try:
        # Update TAB odds and detect scratchings
        update_all_race_odds()
        detect_scratchings()
        
        refresh_race_data()
        entries = RaceEntry.query.filter(RaceEntry.is_scratched == False).order_by(RaceEntry.current_score.desc()).all()
        score_all(entries)
        db.session.commit()
    except Exception as exc:
        flash(f"Auto-refresh failed: {exc}", "warning")
        entries = RaceEntry.query.filter(RaceEntry.is_scratched == False).order_by(RaceEntry.current_score.desc()).limit(100).all()
    
    # Get race categories for filtering
    categories = db.session.query(Race.race_category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template("index.html", entries=entries, categories=categories)


@main_bp.route("/refresh")
def refresh():
    try:
        # Update TAB odds and scratchings first
        update_all_race_odds()
        detect_scratchings()
        
        refresh_race_data()
        entries = RaceEntry.query.all()
        score_all(entries)
        db.session.commit()
        flash("Race data refreshed, odds updated, and scores recalculated.", "success")
    except Exception as exc:
        flash(f"Refresh failed: {exc}", "danger")
    return redirect(url_for("main.index"))


@main_bp.route("/scratchings")
def scratchings():
    """View scratched horses"""
    try:
        scratched_entries = RaceEntry.query.filter(RaceEntry.is_scratched == True).all()
        return render_template("scratchings.html", scratched_entries=scratched_entries)
    except Exception as exc:
        flash(f"Error loading scratchings: {exc}", "danger")
        return redirect(url_for("main.index"))


@main_bp.route("/bets", methods=["GET", "POST"])
def bets():
    if request.method == "POST":
        entry_id = request.form.get("entry_id")
        stake = request.form.get("stake", type=float)
        bet_type = request.form.get("bet_type")
        odds = request.form.get("odds", type=float)
        if not entry_id or not stake or not odds:
            flash("Please fill all bet fields.", "warning")
        else:
            entry = RaceEntry.query.get(entry_id)
            if entry:
                bet = Bet(race_entry_id=entry.id, stake=stake, bet_type=bet_type, market_odds=odds)
                db.session.add(bet)
                db.session.commit()
                flash(f"Bet saved: {bet_type} at {odds} odds.", "success")
            else:
                flash("Selected runner not found.", "danger")
        return redirect(url_for("main.bets"))

    entries = RaceEntry.query.filter(RaceEntry.is_scratched == False).order_by(RaceEntry.current_score.desc()).limit(50).all()
    bets = Bet.query.order_by(Bet.placed_at.desc()).all()
    total_stake = sum(bet.stake for bet in bets)
    total_profit = sum(bet.profit_loss or 0 for bet in bets)
    
    # Calculate stats by bet type
    bet_stats = {}
    for bet in bets:
        if bet.bet_type not in bet_stats:
            bet_stats[bet.bet_type] = {"count": 0, "stake": 0, "profit": 0}
        bet_stats[bet.bet_type]["count"] += 1
        bet_stats[bet.bet_type]["stake"] += bet.stake
        bet_stats[bet.bet_type]["profit"] += bet.profit_loss or 0
    
    return render_template(
        "bets.html",
        entries=entries,
        bets=bets,
        total_stake=total_stake,
        total_profit=total_profit,
        bet_stats=bet_stats,
    )


@main_bp.route("/bet/<int:bet_id>/update", methods=["POST"])
def update_bet(bet_id):
    bet = Bet.query.get_or_404(bet_id)
    bet.result = request.form.get("result")
    profit_loss = request.form.get("profit_loss", type=float)
    if profit_loss is not None:
        bet.profit_loss = profit_loss
    db.session.commit()
    flash("Bet updated.", "success")
    return redirect(url_for("main.bets"))


@main_bp.route("/bonus-bets", methods=["GET", "POST"])
def bonus_bets():
    """Manage bonus bets (multis, parlays, etc.)"""
    if request.method == "POST":
        bet_name = request.form.get("bet_name")
        description = request.form.get("description")
        stake = request.form.get("stake", type=float)
        bet_type = request.form.get("bet_type")  # Multi, Parlay, etc.
        odds = request.form.get("odds", type=float)
        selection_ids = request.form.getlist("selection_ids")
        
        if not bet_name or not stake or not odds or not selection_ids:
            flash("Please fill all bonus bet fields.", "warning")
        else:
            try:
                bonus_bet = BonusBet(
                    bet_name=bet_name,
                    description=description,
                    stake=stake,
                    bet_type=bet_type,
                    selections=selection_ids,
                    odds_combined=odds
                )
                db.session.add(bonus_bet)
                db.session.commit()
                flash(f"Bonus bet '{bet_name}' saved.", "success")
            except Exception as exc:
                flash(f"Error saving bonus bet: {exc}", "danger")
        return redirect(url_for("main.bonus_bets"))
    
    entries = RaceEntry.query.filter(RaceEntry.is_scratched == False).order_by(RaceEntry.current_score.desc()).limit(100).all()
    bonus_bets_list = BonusBet.query.order_by(BonusBet.placed_at.desc()).all()
    
    # Calculate stats
    total_stake = sum(b.stake for b in bonus_bets_list)
    total_profit = sum(b.profit_loss or 0 for b in bonus_bets_list if b.profit_loss is not None)
    unsettled = [b for b in bonus_bets_list if b.result is None]
    
    return render_template(
        "bonus_bets.html",
        entries=entries,
        bonus_bets=bonus_bets_list,
        total_stake=total_stake,
        total_profit=total_profit,
        unsettled_count=len(unsettled),
    )


@main_bp.route("/bonus-bet/<int:bonus_bet_id>/update", methods=["POST"])
def update_bonus_bet(bonus_bet_id):
    """Update bonus bet result"""
    bonus_bet = BonusBet.query.get_or_404(bonus_bet_id)
    bonus_bet.result = request.form.get("result")
    profit_loss = request.form.get("profit_loss", type=float)
    if profit_loss is not None:
        bonus_bet.profit_loss = profit_loss
        bonus_bet.settled_at = datetime.utcnow()
    db.session.commit()
    flash("Bonus bet updated.", "success")
    return redirect(url_for("main.bonus_bets"))


@main_bp.route("/api/odds/<int:entry_id>")
def get_latest_odds(entry_id):
    """API endpoint to get latest odds for a race entry"""
    entry = RaceEntry.query.get_or_404(entry_id)
    return jsonify({
        "horse": entry.horse.name,
        "tab_odds": entry.tab_odds,
        "current_odds": entry.current_odds,
        "scratched": entry.is_scratched,
        "score": entry.current_score,
        "arrow": entry.arrow,
    })
