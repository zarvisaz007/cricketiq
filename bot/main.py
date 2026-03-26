"""
bot/main.py
CricketIQ Telegram Bot entry point.
Menu-driven interface with inline keyboards, background pollers, and rich formatting.

Usage:
    python3 bot/main.py
    (Requires TELEGRAM_BOT_TOKEN in .env)
"""
import sys
import os
import logging

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def run_bot():
    """Start the Telegram bot with all handlers and pollers."""
    if not TOKEN:
        print("[Bot] TELEGRAM_BOT_TOKEN not set in .env")
        print("  Set it: echo 'TELEGRAM_BOT_TOKEN=your_token' >> .env")
        return

    try:
        from telegram.ext import (
            Application, CommandHandler, CallbackQueryHandler,
            MessageHandler, filters,
        )
    except ImportError:
        print("[Bot] python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return

    # Import handler modules
    from frontend.bot.handlers_menu import (
        cmd_start, main_menu_callback, help_callback, help_command, back_callback,
        cmd_predict, cmd_upcoming, cmd_ipl, cmd_live, cmd_dream11,
    )
    from frontend.bot.handlers_upcoming import (
        upcoming_matches, upcoming_page, match_detail,
    )
    from frontend.bot.handlers_predict import (
        predict_from_match, quick_predict_start, quick_predict_manual,
        quick_predict_fmt, quick_predict_t1, quick_predict_t1_page,
        quick_predict_t2, quick_predict_t2_page,
    )
    from frontend.bot.handlers_dream11 import (
        dream11_start, dream11_from_match, dream11_manual,
        dream11_fmt, dream11_t1, dream11_t1_page,
        dream11_t2, dream11_t2_page,
    )
    from frontend.bot.handlers_ipl import (
        ipl_zone, ipl_points_table, ipl_playoff_probs,
        ipl_predictions, ipl_team_rankings,
        ipl_teams_list, ipl_team_detail, ipl_squad,
        ipl_player_profile, ipl_team_stats, ipl_team_form,
        ipl_top_players, ipl_season_overview,
    )
    from frontend.bot.handlers_player import (
        player_lookup_start, player_search_prompt, player_search_text,
        player_browse_start, player_browse_fmt, player_browse_fmt_page,
        player_browse_team, player_browse_team_page, player_profile,
    )
    from frontend.bot.handlers_team import (
        team_analysis_start, team_analysis_fmt, team_analysis_fmt_page,
        team_analysis_team,
    )
    from frontend.bot.handlers_live import live_scores, live_detail
    from frontend.bot.handlers_leaderboard import (
        leaderboards_menu, elo_rankings_start, elo_rankings_fmt,
        top_players_start, top_players_fmt,
    )

    # ── Build application ──────────────────────────────────────

    async def post_init(app):
        """Set bot commands menu and start background pollers."""
        from telegram import BotCommand
        await app.bot.set_my_commands([
            BotCommand("start", "Main menu"),
            BotCommand("help", "How to use CricketIQ"),
            BotCommand("predict", "Match prediction"),
            BotCommand("upcoming", "Upcoming matches"),
            BotCommand("live", "Live scores"),
            BotCommand("ipl", "IPL Zone"),
            BotCommand("dream11", "Dream11 team builder"),
        ])
        logger.info("Bot command menu registered")

        try:
            from scrapers.live_poller import start_poller
            start_poller()
            logger.info("Live score poller started (45s interval)")
        except Exception as e:
            logger.warning(f"Failed to start live poller: {e}")

        try:
            from scrapers.schedule_poller import start_schedule_poller, start_xi_poller
            start_schedule_poller()
            start_xi_poller()
            logger.info("Schedule poller started (6h interval) + XI poller (30min interval)")
        except Exception as e:
            logger.warning(f"Failed to start schedule pollers: {e}")

    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # ── Command handlers ───────────────────────────────────────

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("predict", cmd_predict))
    app.add_handler(CommandHandler("upcoming", cmd_upcoming))
    app.add_handler(CommandHandler("live", cmd_live))
    app.add_handler(CommandHandler("ipl", cmd_ipl))
    app.add_handler(CommandHandler("dream11", cmd_dream11))

    # ── Callback query handlers (pattern-matched) ──────────────

    # Menu navigation
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(back_callback, pattern="^back$"))

    # Upcoming matches
    app.add_handler(CallbackQueryHandler(upcoming_matches, pattern="^upcoming$"))
    app.add_handler(CallbackQueryHandler(upcoming_page, pattern=r"^upcoming_pg\|"))
    app.add_handler(CallbackQueryHandler(match_detail, pattern=r"^match\|"))

    # Predictions
    app.add_handler(CallbackQueryHandler(predict_from_match, pattern=r"^predict_match\|"))
    app.add_handler(CallbackQueryHandler(quick_predict_start, pattern="^quick_predict$"))
    app.add_handler(CallbackQueryHandler(quick_predict_manual, pattern="^qp_manual$"))
    app.add_handler(CallbackQueryHandler(quick_predict_fmt, pattern=r"^qp_fmt\|"))
    app.add_handler(CallbackQueryHandler(quick_predict_t1, pattern=r"^qp_t1\|"))
    app.add_handler(CallbackQueryHandler(quick_predict_t1_page, pattern=r"^qp_t1_pg\|"))
    app.add_handler(CallbackQueryHandler(quick_predict_t2, pattern=r"^qp_t2\|"))
    app.add_handler(CallbackQueryHandler(quick_predict_t2_page, pattern=r"^qp_t2_pg\|"))

    # Dream11
    app.add_handler(CallbackQueryHandler(dream11_start, pattern="^dream11$"))
    app.add_handler(CallbackQueryHandler(dream11_from_match, pattern=r"^d11_match\|"))
    app.add_handler(CallbackQueryHandler(dream11_manual, pattern="^d11_manual$"))
    app.add_handler(CallbackQueryHandler(dream11_fmt, pattern=r"^d11_fmt\|"))
    app.add_handler(CallbackQueryHandler(dream11_t1, pattern=r"^d11_t1\|"))
    app.add_handler(CallbackQueryHandler(dream11_t1_page, pattern=r"^d11_t1_pg\|"))
    app.add_handler(CallbackQueryHandler(dream11_t2, pattern=r"^d11_t2\|"))
    app.add_handler(CallbackQueryHandler(dream11_t2_page, pattern=r"^d11_t2_pg\|"))

    # IPL Zone
    app.add_handler(CallbackQueryHandler(ipl_zone, pattern="^ipl$"))
    app.add_handler(CallbackQueryHandler(ipl_points_table, pattern="^ipl_table$"))
    app.add_handler(CallbackQueryHandler(ipl_playoff_probs, pattern="^ipl_playoffs$"))
    app.add_handler(CallbackQueryHandler(ipl_predictions, pattern="^ipl_predict$"))
    app.add_handler(CallbackQueryHandler(ipl_team_rankings, pattern="^ipl_rankings$"))

    # New IPL handlers
    app.add_handler(CallbackQueryHandler(ipl_teams_list, pattern="^ipl_teams$"))
    app.add_handler(CallbackQueryHandler(ipl_team_detail, pattern=r"^ipl_td\|"))
    app.add_handler(CallbackQueryHandler(ipl_squad, pattern=r"^ipl_sq\|"))
    app.add_handler(CallbackQueryHandler(ipl_player_profile, pattern=r"^ipl_pl\|"))
    app.add_handler(CallbackQueryHandler(ipl_team_stats, pattern=r"^ipl_ts\|"))
    app.add_handler(CallbackQueryHandler(ipl_team_form, pattern=r"^ipl_tf\|"))
    app.add_handler(CallbackQueryHandler(ipl_top_players, pattern="^ipl_top_players$"))
    app.add_handler(CallbackQueryHandler(ipl_season_overview, pattern="^ipl_season_overview$"))

    # Player lookup
    app.add_handler(CallbackQueryHandler(player_lookup_start, pattern="^player$"))
    app.add_handler(CallbackQueryHandler(player_search_prompt, pattern="^pl_search$"))
    app.add_handler(CallbackQueryHandler(player_browse_start, pattern="^pl_browse$"))
    app.add_handler(CallbackQueryHandler(player_browse_fmt, pattern=r"^pl_fmt\|"))
    app.add_handler(CallbackQueryHandler(player_browse_fmt_page, pattern=r"^pl_team_pg\|"))
    app.add_handler(CallbackQueryHandler(player_browse_team, pattern=r"^pl_team\|"))
    app.add_handler(CallbackQueryHandler(player_browse_team_page, pattern=r"^pl_profile_pg\|"))
    app.add_handler(CallbackQueryHandler(player_profile, pattern=r"^pl_profile\|"))

    # Team analysis
    app.add_handler(CallbackQueryHandler(team_analysis_start, pattern="^team_analysis$"))
    app.add_handler(CallbackQueryHandler(team_analysis_fmt, pattern=r"^ta_fmt\|"))
    app.add_handler(CallbackQueryHandler(team_analysis_fmt_page, pattern=r"^ta_team_pg\|"))
    app.add_handler(CallbackQueryHandler(team_analysis_team, pattern=r"^ta_team\|"))

    # Live scores
    app.add_handler(CallbackQueryHandler(live_scores, pattern="^live$"))
    app.add_handler(CallbackQueryHandler(live_detail, pattern=r"^live_detail\|"))

    # Leaderboards
    app.add_handler(CallbackQueryHandler(leaderboards_menu, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(elo_rankings_start, pattern="^lb_elo$"))
    app.add_handler(CallbackQueryHandler(elo_rankings_fmt, pattern=r"^lb_elo\|"))
    app.add_handler(CallbackQueryHandler(top_players_start, pattern="^lb_top$"))
    app.add_handler(CallbackQueryHandler(top_players_fmt, pattern=r"^lb_top\|"))

    # Player text search (MessageHandler for text input)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        player_search_text,
    ))

    # ── Start polling ──────────────────────────────────────────

    logger.info("CricketIQ bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
