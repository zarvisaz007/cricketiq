"""
frontend/bot/handlers_upcoming.py
Upcoming matches browsing + match detail card.
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

from frontend.bot.keyboards import match_list_keyboard, match_action_keyboard, back_and_home_row
from frontend.bot.formatters import format_match_card


async def upcoming_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show paginated list of upcoming matches."""
    q = update.callback_query
    await q.answer()

    context.user_data.setdefault("nav_stack", []).append("main_menu")

    def _fetch():
        from scrapers.cricbuzz_schedule import get_upcoming_matches
        return get_upcoming_matches(days=7)

    matches = await asyncio.to_thread(_fetch)
    context.user_data["upcoming_matches"] = matches

    if not matches:
        await q.edit_message_text(
            "🏏 No upcoming matches found.\n\n"
            "Matches are refreshed every 6 hours.\n"
            "Try again later or check Cricbuzz directly.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    await q.edit_message_text(
        f"🏏 *Upcoming Matches* ({len(matches)} found)\n\nTap a match for details:",
        parse_mode="Markdown",
        reply_markup=match_list_keyboard(matches, page=0),
    )


async def upcoming_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle page navigation for upcoming matches."""
    q = update.callback_query
    await q.answer()

    page = int(q.data.split("|")[1])
    matches = context.user_data.get("upcoming_matches", [])

    if not matches:
        await upcoming_matches(update, context)
        return

    await q.edit_message_text(
        f"🏏 *Upcoming Matches* ({len(matches)} found)\n\nTap a match for details:",
        parse_mode="Markdown",
        reply_markup=match_list_keyboard(matches, page=page),
    )


async def match_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show match detail card with action buttons."""
    q = update.callback_query
    await q.answer()

    cricbuzz_id = q.data.split("|")[1]
    context.user_data.setdefault("nav_stack", []).append("upcoming")

    def _fetch():
        from scrapers.cricbuzz_schedule import get_match_detail
        return get_match_detail(cricbuzz_id)

    match = await asyncio.to_thread(_fetch)

    if not match:
        await q.edit_message_text(
            "❌ Match not found.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    text = format_match_card(match)
    await q.edit_message_text(
        text,
        reply_markup=match_action_keyboard(cricbuzz_id),
    )
