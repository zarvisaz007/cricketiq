"""
frontend/bot/handlers_dream11.py
Dream11 fantasy team generation.
"""
import sys
import os
import asyncio

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from frontend.bot.keyboards import back_and_home_row, format_keyboard, paginated_list_keyboard
from frontend.bot.formatters import format_dream11_team


async def dream11_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dream11 entry — show upcoming matches for selection or manual pick."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("main_menu")

    def _fetch():
        from scrapers.cricbuzz_schedule import get_upcoming_matches
        return get_upcoming_matches(days=7)

    matches = await asyncio.to_thread(_fetch)

    if matches:
        rows = []
        for m in matches[:6]:
            t1, t2 = m["team1"], m["team2"]
            cid = m["cricbuzz_match_id"]
            label = f"🎯 {t1} vs {t2}"
            if len(label) > 50:
                label = f"🎯 {t1[:15]} vs {t2[:15]}"
            rows.append([InlineKeyboardButton(label, callback_data=f"d11_match|{cid}")])
        rows.append([InlineKeyboardButton("✏️ Manual — Pick Teams", callback_data="d11_manual")])
        rows.append(back_and_home_row())

        await q.edit_message_text(
            "🎯 *Dream11 Builder*\n\nPick a match or choose teams manually:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows),
        )
    else:
        await q.edit_message_text(
            "🎯 *Dream11 Builder*\n\nSelect format:",
            parse_mode="Markdown",
            reply_markup=format_keyboard("d11_fmt"),
        )


async def dream11_from_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate Dream11 team from an upcoming match."""
    q = update.callback_query
    await q.answer()

    cricbuzz_id = q.data.split("|")[1]

    await q.edit_message_text("⏳ Building optimal Dream11 team...")

    def _run():
        from scrapers.cricbuzz_schedule import get_match_detail
        match = get_match_detail(cricbuzz_id)
        if not match:
            return None, None

        team1 = match["team1"]
        team2 = match["team2"]
        fmt = match.get("match_type", "T20")
        venue = match.get("venue")

        from fantasy.team_selector import select_dream11_team
        result = select_dream11_team(team1, team2, fmt, venue)
        return match, result

    match, result = await asyncio.to_thread(_run)

    if not match:
        await q.edit_message_text(
            "❌ Match not found.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    header = f"🎯 {match['team1']} vs {match['team2']} ({match.get('match_type', 'T20')})\n\n"
    text = header + format_dream11_team(result) if result else header + "❌ Could not generate team."

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )


async def dream11_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual Dream11 — show format selector."""
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🎯 *Dream11 Builder*\n\nSelect format:",
        parse_mode="Markdown",
        reply_markup=format_keyboard("d11_fmt"),
    )


async def dream11_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Format chosen — show team1 list."""
    q = update.callback_query
    await q.answer()

    fmt = q.data.split("|")[1]
    context.user_data["d11_fmt"] = fmt

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
    context.user_data["d11_teams"] = teams

    await q.edit_message_text(
        f"Format: {fmt}\nSelect Team 1:",
        reply_markup=paginated_list_keyboard(teams, 0, "d11_t1"),
    )


async def dream11_t1_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    teams = context.user_data.get("d11_teams", [])
    await q.edit_message_text(
        "Select Team 1:",
        reply_markup=paginated_list_keyboard(teams, page, "d11_t1"),
    )


async def dream11_t1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Team1 chosen — show team2 list."""
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("|")[1])
    teams = context.user_data.get("d11_teams", [])
    team1 = teams[idx] if idx < len(teams) else "Unknown"
    context.user_data["d11_t1"] = team1

    await q.edit_message_text(
        f"Team 1: {team1}\nSelect Team 2:",
        reply_markup=paginated_list_keyboard(teams, 0, "d11_t2"),
    )


async def dream11_t2_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    teams = context.user_data.get("d11_teams", [])
    await q.edit_message_text(
        "Select Team 2:",
        reply_markup=paginated_list_keyboard(teams, page, "d11_t2"),
    )


async def dream11_t2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Team2 chosen — generate Dream11 team."""
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("|")[1])
    teams = context.user_data.get("d11_teams", [])
    team2 = teams[idx] if idx < len(teams) else "Unknown"
    team1 = context.user_data.get("d11_t1", "Unknown")
    fmt = context.user_data.get("d11_fmt", "T20")

    await q.edit_message_text(f"⏳ Building Dream11 team for {team1} vs {team2}...")

    def _run():
        from fantasy.team_selector import select_dream11_team
        return select_dream11_team(team1, team2, fmt)

    result = await asyncio.to_thread(_run)

    header = f"🎯 {team1} vs {team2} ({fmt})\n\n"
    text = header + format_dream11_team(result) if result else header + "❌ Could not generate team."

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )
