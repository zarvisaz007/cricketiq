"""
frontend/bot/handlers_ipl.py
IPL Zone: points table, playoff probabilities, predictions, team rankings.
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

from frontend.bot.keyboards import ipl_zone_keyboard, back_and_home_row
from frontend.bot.formatters import format_points_table, format_playoff_probs


async def ipl_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show IPL zone sub-menu."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("main_menu")

    await q.edit_message_text(
        "🏆 *IPL Zone*\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=ipl_zone_keyboard(),
    )


async def ipl_points_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show IPL points table."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    await q.edit_message_text("⏳ Loading points table...")

    def _run():
        from features.ipl_season import get_points_table
        return get_points_table()

    table = await asyncio.to_thread(_run)
    text = format_points_table(table)

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Playoff Odds", callback_data="ipl_playoffs")],
            back_and_home_row(),
        ]),
    )


async def ipl_playoff_probs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show playoff qualification probabilities."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    await q.edit_message_text("⏳ Simulating playoff scenarios (5000 sims)...")

    def _run():
        from features.ipl_season import simulate_playoff_probabilities
        return simulate_playoff_probabilities()

    results = await asyncio.to_thread(_run)
    text = format_playoff_probs(results)

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Points Table", callback_data="ipl_table")],
            back_and_home_row(),
        ]),
    )


async def ipl_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show upcoming IPL matches with predict buttons."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    def _fetch():
        from scrapers.cricbuzz_schedule import get_upcoming_matches
        matches = get_upcoming_matches(days=14)
        # Filter for IPL matches
        ipl = [m for m in matches if "ipl" in (m.get("series_name") or "").lower()
               or "indian premier" in (m.get("series_name") or "").lower()]
        # Fallback: include all T20 domestic if no explicit IPL tag
        if not ipl:
            ipl = [m for m in matches if m.get("match_type") == "T20"]
        return ipl[:10]

    matches = await asyncio.to_thread(_fetch)

    if not matches:
        await q.edit_message_text(
            "🔮 No upcoming IPL matches found.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    rows = []
    for m in matches:
        t1, t2 = m["team1"], m["team2"]
        cid = m["cricbuzz_match_id"]
        label = f"🔮 {t1} vs {t2}"
        if len(label) > 50:
            label = f"🔮 {t1[:15]} vs {t2[:15]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"predict_match|{cid}")])
    rows.append(back_and_home_row())

    await q.edit_message_text(
        "🔮 *IPL Predictions*\n\nTap a match to predict:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def ipl_team_rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show IPL franchise strength rankings."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    await q.edit_message_text("⏳ Computing franchise rankings...")

    def _run():
        from features.ipl_features import get_franchise_strength, IPL_HOME_GROUNDS
        teams = list(set(IPL_HOME_GROUNDS.keys()))
        # Deduplicate aliases
        seen = set()
        unique = []
        for t in teams:
            canonical = t
            if canonical not in seen:
                seen.add(canonical)
                unique.append(canonical)

        rankings = []
        for team in unique:
            try:
                strength = get_franchise_strength(team)
                rankings.append({"team": team, "strength": strength})
            except Exception:
                rankings.append({"team": team, "strength": 50.0})

        rankings.sort(key=lambda x: x["strength"], reverse=True)
        return rankings

    rankings = await asyncio.to_thread(_run)

    lines = [
        "🏅 IPL FRANCHISE RANKINGS",
        "",
        f"  {'#':<3} {'Team':<28} Strength",
        "  " + "─" * 42,
    ]
    for i, r in enumerate(rankings, 1):
        team = r["team"]
        s = r["strength"]
        bar_len = max(0, int(s / 100 * 12))
        lines.append(f"  {i:<3} {team:<28} {s:.1f}  {'█' * bar_len}")

    await q.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )
