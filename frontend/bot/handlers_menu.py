"""
frontend/bot/handlers_menu.py
Main menu, /start, /help, back navigation, and slash-command wrappers.
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

from frontend.bot.keyboards import (
    main_menu_keyboard, back_and_home_row, ipl_zone_keyboard,
    match_list_keyboard, live_match_list_keyboard,
)

WELCOME_TEXT = (
    "🏏 *CricketIQ Bot*\n\n"
    "AI-powered cricket prediction engine.\n"
    "4 ML models · 28 features · Dream11 optimizer\n\n"
    "Tap any button below to get started."
)

HELP_TEXT = (
    "ℹ️ *CricketIQ Help*\n\n"
    "*Features:*\n"
    "🏏 Upcoming Matches — Browse scheduled matches\n"
    "🔮 Predictions — 4-model ensemble match prediction\n"
    "📊 Live Scores — Real-time scores from Cricbuzz\n"
    "🏆 IPL Zone — Points table, playoff odds, predictions\n"
    "🎯 Dream11 — Optimal fantasy XI with C/VC picks\n"
    "👤 Player Lookup — Ratings, stats, recent form\n"
    "📈 Team Analysis — Elo, form, squad breakdown\n"
    "🏅 Leaderboards — Top teams & players by rating\n\n"
    "*Commands:*\n"
    "/start — Main menu\n"
    "/help — This help message\n"
    "/predict — Quick prediction\n"
    "/upcoming — Upcoming matches\n"
    "/ipl — IPL Zone\n"
    "/live — Live scores\n"
    "/dream11 — Dream11 builder"
)


# ── Core handlers (callback-based) ────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command — send main menu."""
    context.user_data.clear()
    context.user_data["nav_stack"] = []
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit message to show main menu."""
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    context.user_data["nav_stack"] = []
    await q.edit_message_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help text."""
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        HELP_TEXT,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


# ── Lazy routers (avoid circular imports) ─────────────────────

async def _route_upcoming(update, context):
    from frontend.bot.handlers_upcoming import upcoming_matches
    await upcoming_matches(update, context)


async def _route_ipl(update, context):
    from frontend.bot.handlers_ipl import ipl_zone
    await ipl_zone(update, context)


async def _route_predict(update, context):
    from frontend.bot.handlers_predict import quick_predict_start
    await quick_predict_start(update, context)


async def _route_dream11(update, context):
    from frontend.bot.handlers_dream11 import dream11_start
    await dream11_start(update, context)


async def _route_player(update, context):
    from frontend.bot.handlers_player import player_lookup_start
    await player_lookup_start(update, context)


async def _route_team(update, context):
    from frontend.bot.handlers_team import team_analysis_start
    await team_analysis_start(update, context)


async def _route_leaderboard(update, context):
    from frontend.bot.handlers_leaderboard import leaderboards_menu
    await leaderboards_menu(update, context)


async def _route_live(update, context):
    from frontend.bot.handlers_live import live_scores
    await live_scores(update, context)


# ── Back button dispatch ──────────────────────────────────────

async def _route_ipl_teams(update, context):
    from frontend.bot.handlers_ipl import ipl_teams_list
    await ipl_teams_list(update, context)


async def _route_ipl_team_detail(update, context):
    from frontend.bot.handlers_ipl import ipl_zone
    await ipl_zone(update, context)


async def _route_ipl_squad(update, context):
    from frontend.bot.handlers_ipl import ipl_teams_list
    await ipl_teams_list(update, context)


ROUTES = {
    "main_menu": main_menu_callback,
    "upcoming": _route_upcoming,
    "ipl": _route_ipl,
    "ipl_teams": _route_ipl_teams,
    "ipl_team_detail": _route_ipl_team_detail,
    "ipl_squad": _route_ipl_squad,
    "quick_predict": _route_predict,
    "dream11": _route_dream11,
    "player": _route_player,
    "team_analysis": _route_team,
    "leaderboard": _route_leaderboard,
    "live": _route_live,
}


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back one level using navigation stack with proper dispatch."""
    q = update.callback_query
    await q.answer()
    nav_stack = context.user_data.get("nav_stack", [])

    if not nav_stack:
        await main_menu_callback(update, context)
        return

    prev = nav_stack.pop()
    context.user_data["nav_stack"] = nav_stack

    handler = ROUTES.get(prev, main_menu_callback)
    await handler(update, context)


# ── Slash-command wrappers (reply_text, not edit_message_text) ─

async def cmd_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /predict command — show predictions submenu via message."""
    context.user_data.clear()
    context.user_data["nav_stack"] = []

    def _fetch():
        from scrapers.cricbuzz_schedule import get_upcoming_matches
        return get_upcoming_matches(days=7)

    matches = await asyncio.to_thread(_fetch)

    if matches:
        context.user_data["upcoming_matches"] = matches
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

        await update.message.reply_text(
            "🔮 *Predictions*\n\nPick an upcoming match or choose teams manually:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows),
        )
    else:
        from frontend.bot.keyboards import format_keyboard
        await update.message.reply_text(
            "🔮 *Quick Predict*\n\nNo upcoming matches found. Select format:",
            parse_mode="Markdown",
            reply_markup=format_keyboard("qp_fmt"),
        )


async def cmd_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /upcoming command — fetch and send upcoming matches."""
    context.user_data.clear()
    context.user_data["nav_stack"] = []

    def _fetch():
        from scrapers.cricbuzz_schedule import get_upcoming_matches
        return get_upcoming_matches(days=7)

    matches = await asyncio.to_thread(_fetch)
    context.user_data["upcoming_matches"] = matches

    if not matches:
        await update.message.reply_text(
            "🏏 No upcoming matches found.\n\n"
            "Matches are refreshed every 6 hours.\n"
            "Try again later or check Cricbuzz directly.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    await update.message.reply_text(
        f"🏏 *Upcoming Matches* ({len(matches)} found)\n\nTap a match for details:",
        parse_mode="Markdown",
        reply_markup=match_list_keyboard(matches, page=0),
    )


async def cmd_ipl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ipl command — send IPL zone keyboard."""
    context.user_data.clear()
    context.user_data["nav_stack"] = []
    await update.message.reply_text(
        "🏆 *IPL Zone*\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=ipl_zone_keyboard(),
    )


async def cmd_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /live command — fetch and send live scores."""
    context.user_data.clear()
    context.user_data["nav_stack"] = []

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
        await update.message.reply_text(
            "📊 No live matches right now.\n\n"
            "Check back during match hours!",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    await update.message.reply_text(
        f"📊 *Live Matches* ({len(matches)} active)\n\nTap for scorecard:",
        parse_mode="Markdown",
        reply_markup=live_match_list_keyboard(matches),
    )


async def cmd_dream11(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dream11 command — send Dream11 submenu."""
    context.user_data.clear()
    context.user_data["nav_stack"] = []

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

        await update.message.reply_text(
            "🎯 *Dream11 Builder*\n\nPick a match or choose teams manually:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows),
        )
    else:
        from frontend.bot.keyboards import format_keyboard
        await update.message.reply_text(
            "🎯 *Dream11 Builder*\n\nSelect format:",
            parse_mode="Markdown",
            reply_markup=format_keyboard("d11_fmt"),
        )
