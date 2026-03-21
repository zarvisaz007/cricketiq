"""
frontend/bot/handlers_predict.py
Predictions: from-match (1-tap) + manual quick predict flow.
"""
import sys
import os
import asyncio

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from frontend.bot.keyboards import (
    format_keyboard, paginated_list_keyboard, back_and_home_row,
    match_list_keyboard,
)
from frontend.bot.formatters import format_prediction


def _run_prediction(team1: str, team2: str, fmt: str) -> dict:
    """Run all 4 models + ensemble. Blocking — call via asyncio.to_thread."""
    r = {}

    try:
        from models.elo import win_probability, get_elo
        r["elo_prob"] = win_probability(team1, team2, fmt) * 100
        r["elo1"] = get_elo(team1, fmt)
        r["elo2"] = get_elo(team2, fmt)
    except Exception:
        r["elo_prob"] = 50.0
        r["elo1"] = r["elo2"] = 1500

    try:
        from models.logistic import predict as lr
        r["lr_prob"] = lr(team1, team2, None, fmt, None) * 100
    except Exception:
        r["lr_prob"] = r["elo_prob"]

    try:
        from models.xgboost_model import predict as xgb
        r["xgb_prob"] = xgb(team1, team2, None, fmt, None) * 100
    except Exception:
        r["xgb_prob"] = r["elo_prob"]

    try:
        from simulation.monte_carlo import simulate_match
        mc = simulate_match(team1, team2, fmt, n_simulations=2000)
        r["mc_prob"] = mc["team1_win_pct"]
    except Exception:
        r["mc_prob"] = r["elo_prob"]

    # Ensemble
    probs = [r["elo_prob"], r["lr_prob"], r["xgb_prob"], r["mc_prob"]]
    r["ensemble_prob"] = sum(probs) / len(probs)

    try:
        from features.team_features import get_head_to_head, get_team_recent_form
        r["h2h"] = get_head_to_head(team1, team2, fmt)
        r["form1"] = get_team_recent_form(team1, fmt)
        r["form2"] = get_team_recent_form(team2, fmt)
    except Exception:
        r["h2h"] = {"total": 0}

    return r


# ── Predict from upcoming match (1-tap) ──────────────────────

async def predict_from_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Predict outcome for an upcoming match by cricbuzz ID."""
    q = update.callback_query
    await q.answer()

    cricbuzz_id = q.data.split("|")[1]
    context.user_data.setdefault("nav_stack", []).append("upcoming")

    await q.edit_message_text("⏳ Running 4-model ensemble prediction...")

    def _fetch_and_predict():
        from scrapers.cricbuzz_schedule import get_match_detail
        match = get_match_detail(cricbuzz_id)
        if not match:
            return None, None
        team1 = match["team1"]
        team2 = match["team2"]
        fmt = match.get("match_type", "T20")
        result = _run_prediction(team1, team2, fmt)
        return match, result

    match, result = await asyncio.to_thread(_fetch_and_predict)

    if not match:
        await q.edit_message_text(
            "❌ Match not found.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    text = format_prediction(match["team1"], match["team2"],
                             match.get("match_type", "T20"), result)
    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )


# ── Quick Predict (manual) ───────────────────────────────────

async def quick_predict_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start manual prediction — format selector."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("main_menu")

    # Check if there are upcoming matches to offer as shortcuts
    def _fetch():
        from scrapers.cricbuzz_schedule import get_upcoming_matches
        return get_upcoming_matches(days=7)

    matches = await asyncio.to_thread(_fetch)

    if matches:
        context.user_data["upcoming_matches"] = matches
        # Show upcoming matches + manual option
        from telegram import InlineKeyboardButton
        rows = []
        for m in matches[:5]:
            t1, t2 = m["team1"], m["team2"]
            cid = m["cricbuzz_match_id"]
            label = f"🏏 {t1} vs {t2}"
            if len(label) > 50:
                label = f"🏏 {t1[:15]} vs {t2[:15]}"
            rows.append([InlineKeyboardButton(label, callback_data=f"predict_match|{cid}")])
        rows.append([InlineKeyboardButton("✏️ Manual — Pick Teams", callback_data="qp_manual")])
        rows.append(back_and_home_row())

        await q.edit_message_text(
            "🔮 *Predictions*\n\nPick an upcoming match or choose teams manually:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows),
        )
    else:
        await q.edit_message_text(
            "🔮 *Quick Predict*\n\nSelect format:",
            parse_mode="Markdown",
            reply_markup=format_keyboard("qp_fmt"),
        )


async def quick_predict_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual predict — show format selector."""
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🔮 *Quick Predict*\n\nSelect format:",
        parse_mode="Markdown",
        reply_markup=format_keyboard("qp_fmt"),
    )


async def quick_predict_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Format chosen — show team1 list."""
    q = update.callback_query
    await q.answer()

    fmt = q.data.split("|")[1]
    context.user_data["qp_fmt"] = fmt

    def _fetch():
        from database.db import get_connection
        cf = "AND competition = 'T20I'" if fmt == "T20" else ("AND competition = 'ODI'" if fmt == "ODI" else "")
        conn = get_connection()
        rows = conn.execute(f"""
            SELECT DISTINCT team1 AS team FROM matches
            WHERE match_type = ? AND gender = 'male' {cf}
            UNION
            SELECT DISTINCT team2 AS team FROM matches
            WHERE match_type = ? AND gender = 'male' {cf}
            ORDER BY team
        """, (fmt, fmt)).fetchall()
        conn.close()
        return [r["team"] for r in rows]

    teams = await asyncio.to_thread(_fetch)
    context.user_data["qp_teams"] = teams

    await q.edit_message_text(
        f"Format: {fmt}\nSelect Team 1 ({len(teams)} teams):",
        reply_markup=paginated_list_keyboard(teams, 0, "qp_t1"),
    )


async def quick_predict_t1_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paginate team1 list."""
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    teams = context.user_data.get("qp_teams", [])
    await q.edit_message_text(
        "Select Team 1:",
        reply_markup=paginated_list_keyboard(teams, page, "qp_t1"),
    )


async def quick_predict_t1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Team1 chosen — show team2 list."""
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("|")[1])
    teams = context.user_data.get("qp_teams", [])
    team1 = teams[idx] if idx < len(teams) else "Unknown"
    context.user_data["qp_t1"] = team1

    await q.edit_message_text(
        f"Team 1: {team1}\nSelect Team 2:",
        reply_markup=paginated_list_keyboard(teams, 0, "qp_t2"),
    )


async def quick_predict_t2_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paginate team2 list."""
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    teams = context.user_data.get("qp_teams", [])
    await q.edit_message_text(
        "Select Team 2:",
        reply_markup=paginated_list_keyboard(teams, page, "qp_t2"),
    )


async def quick_predict_t2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Team2 chosen — run prediction."""
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("|")[1])
    teams = context.user_data.get("qp_teams", [])
    team2 = teams[idx] if idx < len(teams) else "Unknown"
    team1 = context.user_data.get("qp_t1", "Unknown")
    fmt = context.user_data.get("qp_fmt", "T20")

    await q.edit_message_text(f"⏳ Predicting {team1} vs {team2} ({fmt})...")

    result = await asyncio.to_thread(_run_prediction, team1, team2, fmt)

    text = format_prediction(team1, team2, fmt, result)
    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )
