"""
frontend/bot/handlers_leaderboard.py
Elo rankings + top players leaderboards.
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

from frontend.bot.keyboards import leaderboard_keyboard, format_keyboard, back_and_home_row
from frontend.bot.formatters import format_elo_rankings, format_top_players


async def leaderboards_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show leaderboard sub-menu."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("main_menu")

    await q.edit_message_text(
        "🏅 *Leaderboards*\n\nChoose a leaderboard:",
        parse_mode="Markdown",
        reply_markup=leaderboard_keyboard(),
    )


async def elo_rankings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elo rankings — format selector."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("leaderboard")

    await q.edit_message_text(
        "🏅 Elo Rankings\n\nSelect format:",
        reply_markup=format_keyboard("lb_elo"),
    )


async def elo_rankings_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Format chosen — show Elo rankings."""
    q = update.callback_query
    await q.answer()

    fmt = q.data.split("|")[1]

    await q.edit_message_text(f"⏳ Loading {fmt} Elo rankings...")

    def _run():
        from models.elo import get_top_elo_rankings
        return get_top_elo_rankings(fmt, n=20)

    rankings = await asyncio.to_thread(_run)
    text = format_elo_rankings(rankings, fmt)

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )


async def top_players_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Top players — format selector."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("leaderboard")

    await q.edit_message_text(
        "⭐ Top Players\n\nSelect format:",
        reply_markup=format_keyboard("lb_top"),
    )


async def top_players_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Format chosen — show top players."""
    q = update.callback_query
    await q.answer()

    fmt = q.data.split("|")[1]

    await q.edit_message_text(f"⏳ Loading top {fmt} players...")

    def _run():
        from ratings.player_ratings import get_top_players
        return get_top_players(fmt, n=20, role="overall")

    players = await asyncio.to_thread(_run)
    text = format_top_players(players, fmt)

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )
