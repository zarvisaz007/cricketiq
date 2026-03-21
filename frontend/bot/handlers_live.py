"""
frontend/bot/handlers_live.py
Live scores: match list + scorecard detail.
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

from frontend.bot.keyboards import live_match_list_keyboard, back_and_home_row
from frontend.bot.formatters import format_live_scorecard


async def live_scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of live matches."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("main_menu")

    def _fetch():
        from scrapers.cricbuzz_live import get_live_matches
        return get_live_matches()

    matches = await asyncio.to_thread(_fetch)

    if not matches:
        # Try cached
        def _cached():
            from scrapers.live_poller import get_cached_live_matches
            return get_cached_live_matches()

        matches = await asyncio.to_thread(_cached)

    if not matches:
        await q.edit_message_text(
            "📊 No live matches right now.\n\n"
            "Check back during match hours!",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    await q.edit_message_text(
        f"📊 *Live Matches* ({len(matches)} active)\n\nTap for scorecard:",
        parse_mode="Markdown",
        reply_markup=live_match_list_keyboard(matches),
    )


async def live_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show live scorecard for a specific match."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("live")

    cricbuzz_id = q.data.split("|")[1]

    await q.edit_message_text("⏳ Fetching live scorecard...")

    def _fetch():
        from scrapers.cricbuzz_live import fetch_live_scorecard
        return fetch_live_scorecard(cricbuzz_id)

    scorecard = await asyncio.to_thread(_fetch)

    if not scorecard:
        # Try from DB cache
        def _cached():
            from database.db import get_connection
            conn = get_connection()
            row = conn.execute(
                "SELECT * FROM live_matches WHERE cricbuzz_match_id = ?",
                (cricbuzz_id,)
            ).fetchone()
            conn.close()
            return dict(row) if row else None

        cached = await asyncio.to_thread(_cached)
        if cached:
            text = (
                f"🔴 {cached.get('team1', '?')} vs {cached.get('team2', '?')}\n\n"
                f"{cached.get('score_summary', 'Score unavailable')}"
            )
        else:
            text = "❌ Scorecard unavailable."
    else:
        text = format_live_scorecard(scorecard)

    from telegram import InlineKeyboardButton
    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"live_detail|{cricbuzz_id}")],
            back_and_home_row(),
        ]),
    )
