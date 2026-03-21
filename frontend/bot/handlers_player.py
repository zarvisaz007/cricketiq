"""
frontend/bot/handlers_player.py
Player lookup: search by name + browse by team.
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
    player_lookup_keyboard, format_keyboard, paginated_list_keyboard, back_and_home_row,
)
from frontend.bot.formatters import format_player_profile

# State constant for player search text input
PLAYER_SEARCH_STATE = 100


async def player_lookup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Player lookup entry — search or browse."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("main_menu")

    await q.edit_message_text(
        "👤 *Player Lookup*\n\nSearch by name or browse by team:",
        parse_mode="Markdown",
        reply_markup=player_lookup_keyboard(),
    )


async def player_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to type a player name."""
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting_player_search"] = True

    await q.edit_message_text(
        "🔍 Type a player name to search:\n\n(Send a text message with the player's name)",
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )


async def player_search_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for player search — fuzzy match against DB."""
    if not context.user_data.get("awaiting_player_search"):
        return  # Not in search mode

    context.user_data["awaiting_player_search"] = False
    query = update.message.text.strip()

    if not query or len(query) < 2:
        await update.message.reply_text(
            "Please enter at least 2 characters.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    def _search():
        from database.db import get_connection
        conn = get_connection()
        # Fuzzy search using LIKE
        rows = conn.execute("""
            SELECT DISTINCT player_name FROM player_ratings
            WHERE player_name LIKE ?
            ORDER BY overall_rating DESC
            LIMIT 20
        """, (f"%{query}%",)).fetchall()
        conn.close()
        return [r["player_name"] for r in rows]

    results = await asyncio.to_thread(_search)

    if not results:
        await update.message.reply_text(
            f"No players found matching '{query}'.\nTry a different spelling.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    context.user_data["pl_results"] = results
    context.user_data["pl_fmt"] = "T20"  # Default format

    await update.message.reply_text(
        f"Found {len(results)} player(s) matching '{query}':",
        reply_markup=paginated_list_keyboard(results, 0, "pl_profile"),
    )


async def player_browse_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse by team — show format selector."""
    q = update.callback_query
    await q.answer()

    await q.edit_message_text(
        "👤 Browse Players\n\nSelect format:",
        reply_markup=format_keyboard("pl_fmt"),
    )


async def player_browse_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Format chosen — show team list."""
    q = update.callback_query
    await q.answer()

    fmt = q.data.split("|")[1]
    context.user_data["pl_fmt"] = fmt

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
    context.user_data["pl_teams"] = teams

    await q.edit_message_text(
        f"Format: {fmt}\nSelect team:",
        reply_markup=paginated_list_keyboard(teams, 0, "pl_team"),
    )


async def player_browse_fmt_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paginate team list."""
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    teams = context.user_data.get("pl_teams", [])
    await q.edit_message_text(
        "Select team:",
        reply_markup=paginated_list_keyboard(teams, page, "pl_team"),
    )


async def player_browse_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Team chosen — show players list."""
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("|")[1])
    teams = context.user_data.get("pl_teams", [])
    team = teams[idx] if idx < len(teams) else "Unknown"
    fmt = context.user_data.get("pl_fmt", "T20")
    context.user_data["pl_team_name"] = team

    def _fetch():
        from database.db import get_connection
        cf = "AND competition = 'T20I'" if fmt == "T20" else ("AND competition = 'ODI'" if fmt == "ODI" else "")
        conn = get_connection()
        rows = conn.execute(f"""
            SELECT pms.player_name, COUNT(DISTINCT m.id) AS g
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.id
            WHERE pms.team = ? AND m.match_type = ? AND m.gender = 'male' {cf}
            GROUP BY pms.player_name
            ORDER BY g DESC
            LIMIT 60
        """, (team, fmt)).fetchall()
        conn.close()
        return [r["player_name"] for r in rows]

    players = await asyncio.to_thread(_fetch)
    context.user_data["pl_players"] = players

    await q.edit_message_text(
        f"Team: {team}\nSelect player ({len(players)}):",
        reply_markup=paginated_list_keyboard(players, 0, "pl_profile"),
    )


async def player_browse_team_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paginate players list."""
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    players = context.user_data.get("pl_players", context.user_data.get("pl_results", []))
    await q.edit_message_text(
        "Select player:",
        reply_markup=paginated_list_keyboard(players, page, "pl_profile"),
    )


async def player_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full player profile."""
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("|")[1])
    # Try browse list first, then search results
    players = context.user_data.get("pl_players", context.user_data.get("pl_results", []))
    player = players[idx] if idx < len(players) else "Unknown"
    fmt = context.user_data.get("pl_fmt", "T20")

    await q.edit_message_text(f"⏳ Loading profile: {player}...")

    def _run():
        from ratings.player_ratings import get_player_rating
        from features.player_features import get_batting_stats, get_bowling_stats, get_player_role

        rating = get_player_rating(player, fmt)
        batting = get_batting_stats(player, fmt)
        bowling = get_bowling_stats(player, fmt)
        role = get_player_role(player, fmt)
        rating["role"] = role
        return rating, batting, bowling

    rating, batting, bowling = await asyncio.to_thread(_run)

    text = format_player_profile(player, fmt, rating, batting, bowling)

    # Send as new message if too long, else edit
    if len(text) > 4000:
        await q.edit_message_text("📋 Full profile below:")
        for i in range(0, len(text), 4000):
            await q.message.reply_text(text[i:i+4000])
        from telegram import InlineKeyboardButton
        await q.message.reply_text(
            "↩️",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
    else:
        await q.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
