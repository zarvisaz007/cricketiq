"""
bot/main.py
CricketIQ Telegram Bot entry point.
Provides: Predict, Live Scores, Player Report, Dream11 Team, IPL Zone, Leaderboards.

Usage:
    python3 bot/main.py
    (Requires TELEGRAM_BOT_TOKEN in .env)
"""
import sys
import os
import asyncio
import logging

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def run_bot():
    """Start the Telegram bot."""
    if not TOKEN:
        print("[Bot] TELEGRAM_BOT_TOKEN not set in .env")
        print("  Set it: echo 'TELEGRAM_BOT_TOKEN=your_token' >> .env")
        return

    try:
        from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                                  MessageHandler, filters, ConversationHandler)
    except ImportError:
        print("[Bot] python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return

    # Import handlers from existing bot module
    try:
        from frontend.bot.handlers import (
            start_handler, help_handler, predict_handler, player_handler,
            team_handler, top_handler, alerts_handler, elo_handler, pvor_handler,
        )
        has_handlers = True
    except ImportError:
        has_handlers = False

    app = Application.builder().token(TOKEN).build()

    if has_handlers:
        # Register existing conversation handlers
        for handler in [predict_handler, player_handler, team_handler,
                        top_handler, alerts_handler, elo_handler, pvor_handler]:
            app.add_handler(handler)
        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CommandHandler("help", help_handler))
    else:
        # Minimal handlers
        async def cmd_start(update, context):
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("Match Prediction", callback_data="predict"),
                 InlineKeyboardButton("Live Scores", callback_data="live")],
                [InlineKeyboardButton("Player Report", callback_data="player"),
                 InlineKeyboardButton("Dream11 Team", callback_data="dream11")],
                [InlineKeyboardButton("IPL Zone", callback_data="ipl"),
                 InlineKeyboardButton("Leaderboards", callback_data="leaderboard")],
            ]
            await update.message.reply_text(
                "Welcome to CricketIQ v2!\nChoose an option:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        async def cmd_help(update, context):
            await update.message.reply_text(
                "CricketIQ v2 — Cricket Prediction Bot\n\n"
                "Commands:\n"
                "/start - Main menu\n"
                "/help - This help message\n\n"
                "Features:\n"
                "- Match predictions (Elo + XGBoost + Monte Carlo)\n"
                "- Live scores from Cricbuzz\n"
                "- Player analysis & PVOR\n"
                "- Dream11 team builder\n"
                "- IPL zone (points table, playoff probabilities)\n"
                "- Team & player leaderboards"
            )

        async def handle_callback(update, context):
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                f"Feature '{query.data}' selected.\n"
                "Use the CLI for full functionality: python3 frontend/test_cli.py"
            )

        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("help", cmd_help))
        app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("CricketIQ bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
