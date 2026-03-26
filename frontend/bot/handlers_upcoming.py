"""
frontend/bot/handlers_upcoming.py
Upcoming matches browsing + rich match detail report.
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
from frontend.bot.formatters import format_rich_match_report

# Telegram message length limit
TG_MAX_LEN = 4096


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


def _split_message(text: str, max_len: int = TG_MAX_LEN) -> list:
    """Split text into chunks that fit within Telegram's message limit."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_len and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks


async def match_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show rich match report with prediction, form, and match info."""
    q = update.callback_query
    await q.answer()

    cricbuzz_id = q.data.split("|")[1]
    context.user_data.setdefault("nav_stack", []).append("upcoming")

    await q.edit_message_text("⏳ Loading match analysis...")

    def _fetch():
        from scrapers.cricbuzz_schedule import get_match_detail
        match = get_match_detail(cricbuzz_id)
        if not match:
            return None, None, None, None

        team1, team2 = match["team1"], match["team2"]
        fmt = match.get("match_type", "T20")

        # Run prediction
        from frontend.bot.handlers_predict import _run_prediction
        prediction = _run_prediction(team1, team2, fmt)

        # Fetch team forms
        from features.team_features import get_team_recent_form
        try:
            form1 = get_team_recent_form(team1, fmt)
        except Exception:
            form1 = None
        try:
            form2 = get_team_recent_form(team2, fmt)
        except Exception:
            form2 = None

        return match, prediction, form1, form2

    match, prediction, form1, form2 = await asyncio.to_thread(_fetch)

    if not match:
        await q.edit_message_text(
            "❌ Match not found.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    text = format_rich_match_report(match, prediction, form1, form2)
    keyboard = match_action_keyboard(cricbuzz_id)

    # Handle the 4096-char limit
    chunks = _split_message(text)

    if len(chunks) == 1:
        await q.edit_message_text(
            chunks[0],
            reply_markup=keyboard,
        )
    else:
        # First chunk edits the existing message (no keyboard)
        await q.edit_message_text(chunks[0])
        # Middle chunks sent as new messages (no keyboard)
        chat = update.effective_chat
        for chunk in chunks[1:-1]:
            await chat.send_message(chunk)
        # Last chunk gets the action keyboard
        await chat.send_message(
            chunks[-1],
            reply_markup=keyboard,
        )
