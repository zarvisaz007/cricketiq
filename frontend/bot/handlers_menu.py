"""
frontend/bot/handlers_menu.py
Main menu, /start, /help, back navigation.
"""
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from telegram import Update
from telegram.ext import ContextTypes

from frontend.bot.keyboards import main_menu_keyboard

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
    "/help — This help message"
)


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
    from frontend.bot.keyboards import back_and_home_row
    from telegram import InlineKeyboardMarkup
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


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back one level using navigation stack."""
    q = update.callback_query
    await q.answer()
    nav_stack = context.user_data.get("nav_stack", [])

    if nav_stack:
        prev = nav_stack.pop()
        context.user_data["nav_stack"] = nav_stack
        # Re-trigger the previous callback
        q.data = prev
        # Route to main menu as fallback
        await main_menu_callback(update, context)
    else:
        await main_menu_callback(update, context)
