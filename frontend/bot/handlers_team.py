"""
frontend/bot/handlers_team.py
Team analysis: Elo + form + squad ratings + key players.
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

from frontend.bot.keyboards import format_keyboard, paginated_list_keyboard, back_and_home_row
from frontend.bot.formatters import format_team_analysis


async def team_analysis_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Team analysis entry — show format selector."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("main_menu")

    await q.edit_message_text(
        "📈 *Team Analysis*\n\nSelect format:",
        parse_mode="Markdown",
        reply_markup=format_keyboard("ta_fmt"),
    )


async def team_analysis_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Format chosen — show team list."""
    q = update.callback_query
    await q.answer()

    fmt = q.data.split("|")[1]
    context.user_data["ta_fmt"] = fmt

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
    context.user_data["ta_teams"] = teams

    await q.edit_message_text(
        f"Format: {fmt}\nSelect team ({len(teams)}):",
        reply_markup=paginated_list_keyboard(teams, 0, "ta_team"),
    )


async def team_analysis_fmt_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paginate team list."""
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    teams = context.user_data.get("ta_teams", [])
    await q.edit_message_text(
        "Select team:",
        reply_markup=paginated_list_keyboard(teams, page, "ta_team"),
    )


async def team_analysis_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Team chosen — run full analysis."""
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("|")[1])
    teams = context.user_data.get("ta_teams", [])
    team = teams[idx] if idx < len(teams) else "Unknown"
    fmt = context.user_data.get("ta_fmt", "T20")

    await q.edit_message_text(f"⏳ Analysing {team} ({fmt})...")

    def _run():
        from features.team_features import get_team_recent_form, get_team_squad
        from ratings.player_ratings import get_player_rating
        from models.elo import get_elo

        elo = get_elo(team, fmt)
        form = get_team_recent_form(team, fmt, n=10)
        squad = get_team_squad(team, fmt, last_n_matches=5)[:15]
        ratings = [get_player_rating(p, fmt) for p in squad] if squad else []
        return elo, form, squad, ratings

    elo, form, squad, ratings = await asyncio.to_thread(_run)

    text = format_team_analysis(team, fmt, elo, form, squad, ratings)

    if len(text) > 4000:
        await q.edit_message_text("📋 Full analysis below:")
        for i in range(0, len(text), 4000):
            await q.message.reply_text(text[i:i+4000])
        await q.message.reply_text(
            "↩️",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
    else:
        await q.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
