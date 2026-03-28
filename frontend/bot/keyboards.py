"""
frontend/bot/keyboards.py
Centralized inline keyboard builders for the CricketIQ Telegram bot.
"""
import math
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

PAGE_SIZE = 8


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu 5x2 grid."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏏 Upcoming Matches", callback_data="upcoming"),
         InlineKeyboardButton("🔮 Predictions", callback_data="quick_predict")],
        [InlineKeyboardButton("📊 Live Scores", callback_data="live"),
         InlineKeyboardButton("🏆 IPL Zone", callback_data="ipl")],
        [InlineKeyboardButton("🎯 Dream11 Builder", callback_data="dream11"),
         InlineKeyboardButton("👤 Player Lookup", callback_data="player")],
        [InlineKeyboardButton("📈 Team Analysis", callback_data="team_analysis"),
         InlineKeyboardButton("🏅 Leaderboards", callback_data="leaderboard")],
        [InlineKeyboardButton("⚡ Quick Predict", callback_data="quick_predict"),
         InlineKeyboardButton("ℹ️ Help", callback_data="help")],
    ])


def back_and_home_row() -> list:
    """Returns [Back, Main Menu] button row."""
    return [
        InlineKeyboardButton("⬅️ Back", callback_data="back"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
    ]





def match_list_keyboard(matches: list, page: int = 0,
                        prefix: str = "match") -> InlineKeyboardMarkup:
    """Paginated upcoming match list.
    Button labels now include day + time: "CSK vs MI · Fri 04 Apr, 19:30"
    """
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, len(matches))
    rows = []

    for m in matches[start:end]:
        team1 = m.get("team1", "?")
        team2 = m.get("team2", "?")
        start_time = m.get("start_time", "")
        match_type = m.get("match_type", "")

        # Build suffix: "dd/mm/yy · IPL"
        suffix_parts = []
        if start_time:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                    .replace("+00:00", ""))
                suffix_parts.append(dt.strftime("%d/%m/%y"))
            except (ValueError, TypeError):
                pass
        if match_type:
            suffix_parts.append(match_type)
        suffix = f" · {' · '.join(suffix_parts)}" if suffix_parts else ""

        label = f"{team1} vs {team2}{suffix}"
        # Telegram limits button labels — truncate team names if needed
        if len(label) > 55:
            label = f"{team1[:12]} vs {team2[:12]}{suffix}"
        if len(label) > 55:
            label = label[:52] + "..."
        cid = m.get("cricbuzz_match_id", "")
        rows.append([InlineKeyboardButton(
            label, callback_data=f"{prefix}|{cid}")])

    # Pagination
    nav = []
    total_pages = math.ceil(len(matches) / PAGE_SIZE) if matches else 1
    if page > 0:
        nav.append(InlineKeyboardButton(
            "◀ Prev", callback_data=f"upcoming_pg|{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "Next ▶", callback_data=f"upcoming_pg|{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append(back_and_home_row())
    return InlineKeyboardMarkup(rows)


def match_action_keyboard(cricbuzz_id: str) -> InlineKeyboardMarkup:
    """Action buttons for a match detail card."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔮 Predict", callback_data=f"predict_match|{cricbuzz_id}"),
         InlineKeyboardButton(
            "🎯 Dream11", callback_data=f"d11_match|{cricbuzz_id}")],
        [InlineKeyboardButton(
            "📊 H2H", callback_data=f"predict_match|{cricbuzz_id}"),
         InlineKeyboardButton(
            "📈 Teams", callback_data="team_analysis")],
        back_and_home_row(),
    ])


def ipl_zone_keyboard() -> InlineKeyboardMarkup:
    """IPL zone sub-menu — expanded 4-row layout."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Points Table", callback_data="ipl_table"),
         InlineKeyboardButton("🎲 Playoff Odds", callback_data="ipl_playoffs")],
        [InlineKeyboardButton("🔮 IPL Predictions", callback_data="ipl_predict"),
         InlineKeyboardButton("🏅 Team Rankings", callback_data="ipl_rankings")],
        [InlineKeyboardButton("🏏 Browse Teams", callback_data="ipl_teams"),
         InlineKeyboardButton("⭐ Top IPL Players", callback_data="ipl_top_players")],
        back_and_home_row(),
    ])


def ipl_teams_keyboard(teams: list) -> InlineKeyboardMarkup:
    """List of IPL teams as buttons using indices (keeps callback_data short).

    Parameters
    ----------
    teams : list
        List of team name strings, e.g. ["Chennai Super Kings", "Mumbai Indians", ...]
    """
    rows = []
    for idx, team_name in enumerate(teams):
        label = team_name if len(team_name) <= 40 else team_name[:37] + "..."
        # Using index keeps callback_data well under 64-byte limit
        rows.append([InlineKeyboardButton(
            f"🏏 {label}", callback_data=f"ipl_tm|{idx}")])

    rows.append(back_and_home_row())
    return InlineKeyboardMarkup(rows)


def ipl_team_detail_keyboard(idx: int) -> InlineKeyboardMarkup:
    """Detail actions for a specific IPL team.
    Uses team index (not name) to stay under Telegram's 64-byte
    callback_data limit.

    Parameters
    ----------
    idx : int
        Index of the team in the teams list.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📋 Squad", callback_data=f"ipl_sq|{idx}"),
         InlineKeyboardButton(
            "📊 Stats", callback_data=f"ipl_st|{idx}")],
        [InlineKeyboardButton(
            "📅 Next Match", callback_data=f"ipl_nx|{idx}"),
         InlineKeyboardButton(
            "🔥 Form", callback_data=f"ipl_fm|{idx}")],
        back_and_home_row(),
    ])


def format_keyboard(prefix: str = "qp_fmt") -> InlineKeyboardMarkup:
    """T20 / ODI format selector."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("T20", callback_data=f"{prefix}|T20"),
         InlineKeyboardButton("ODI", callback_data=f"{prefix}|ODI")],
        back_and_home_row(),
    ])


def paginated_list_keyboard(items: list, page: int, prefix: str,
                            per_page: int = PAGE_SIZE) -> InlineKeyboardMarkup:
    """Generic paginated list keyboard using indices for short callback data."""
    start = page * per_page
    end = min(start + per_page, len(items))
    rows = []

    for i, item in enumerate(items[start:end], start=start):
        label = item if len(item) <= 45 else item[:42] + "..."
        rows.append([InlineKeyboardButton(
            label, callback_data=f"{prefix}|{i}")])

    nav = []
    total_pages = math.ceil(len(items) / per_page) if items else 1
    if page > 0:
        nav.append(InlineKeyboardButton(
            "◀ Prev", callback_data=f"{prefix}_pg|{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "Next ▶", callback_data=f"{prefix}_pg|{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append(back_and_home_row())
    return InlineKeyboardMarkup(rows)


def leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Leaderboard sub-menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏅 Elo Rankings", callback_data="lb_elo"),
         InlineKeyboardButton("⭐ Top Players", callback_data="lb_top")],
        back_and_home_row(),
    ])


def player_lookup_keyboard() -> InlineKeyboardMarkup:
    """Player lookup start menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search by Name", callback_data="pl_search"),
         InlineKeyboardButton("📋 Browse by Team", callback_data="pl_browse")],
        back_and_home_row(),
    ])


def live_match_list_keyboard(matches: list) -> InlineKeyboardMarkup:
    """List of live matches with detail buttons."""
    rows = []
    for m in matches[:10]:
        t1 = m.get("team1", "?")
        t2 = m.get("team2", "?")
        label = f"🔴 {t1} vs {t2}"
        if len(label) > 50:
            label = f"🔴 {t1[:15]} vs {t2[:15]}"
        cid = m.get("cricbuzz_match_id", m.get("cricbuzz_id", ""))
        rows.append([InlineKeyboardButton(
            label, callback_data=f"live_detail|{cid}")])

    rows.append(back_and_home_row())
    return InlineKeyboardMarkup(rows)
