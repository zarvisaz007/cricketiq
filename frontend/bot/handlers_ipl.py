"""
frontend/bot/handlers_ipl.py
IPL Hub: points table, playoff probabilities, predictions, team rankings,
team browser, squad viewer, player profiles, team stats/form, top players,
season overview.
"""
from __future__ import annotations

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
    ipl_zone_keyboard,
    back_and_home_row,
    paginated_list_keyboard,
)
from frontend.bot.formatters import (
    format_points_table,
    format_playoff_probs,
    format_player_profile,
    format_team_analysis,
    bar,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Canonical IPL team list (deduplicated from IPL_HOME_GROUNDS keys).
# Built once at import time.

_CANONICAL_IPL_TEAMS: list[str] | None = None


def _get_canonical_teams() -> list[str]:
    """Return a stable, deduplicated list of canonical IPL team names."""
    global _CANONICAL_IPL_TEAMS
    if _CANONICAL_IPL_TEAMS is not None:
        return _CANONICAL_IPL_TEAMS

    from features.ipl_features import IPL_HOME_GROUNDS

    # Map ground -> first team name seen (canonical)
    ground_to_team: dict[str, str] = {}
    for team, ground in IPL_HOME_GROUNDS.items():
        if ground not in ground_to_team:
            ground_to_team[ground] = team

    _CANONICAL_IPL_TEAMS = sorted(ground_to_team.values())
    return _CANONICAL_IPL_TEAMS


def _role_emoji(role: str) -> str:
    role_lower = role.lower() if role else ""
    if "bat" in role_lower:
        return "\U0001f3cf"   # cricket bat
    if "bowl" in role_lower:
        return "\u26be"       # baseball (closest to bowling)
    if "all" in role_lower:
        return "\u2b50"       # star
    if "keeper" in role_lower or "wk" in role_lower:
        return "\U0001f9e4"   # gloves
    return "\U0001f464"       # person


def _wl_indicator(wins: list[bool]) -> str:
    """Return a visual W/L string for a list of booleans (True=win)."""
    return " ".join("\u2705" if w else "\u274c" for w in wins)


# ---------------------------------------------------------------------------
# 0. IPL Zone (existing — updated with new buttons)
# ---------------------------------------------------------------------------

async def ipl_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show IPL zone sub-menu."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("main_menu")

    await q.edit_message_text(
        "\U0001f3c6 *IPL Hub*\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=ipl_zone_keyboard(),
    )


# ---------------------------------------------------------------------------
# 1. Points Table (existing)
# ---------------------------------------------------------------------------

async def ipl_points_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show IPL points table."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    await q.edit_message_text("\u23f3 Loading points table...")

    def _run():
        from features.ipl_season import get_points_table
        return get_points_table()

    table = await asyncio.to_thread(_run)
    text = format_points_table(table)

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f3b2 Playoff Odds", callback_data="ipl_playoffs")],
            [InlineKeyboardButton("\U0001f4c5 Season Overview", callback_data="ipl_season_overview")],
            back_and_home_row(),
        ]),
    )


# ---------------------------------------------------------------------------
# 2. Playoff Probabilities (existing)
# ---------------------------------------------------------------------------

async def ipl_playoff_probs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show playoff qualification probabilities."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    await q.edit_message_text("\u23f3 Simulating playoff scenarios (5 000 sims)...")

    def _run():
        from features.ipl_season import simulate_playoff_probabilities
        return simulate_playoff_probabilities()

    results = await asyncio.to_thread(_run)
    text = format_playoff_probs(results)

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f4ca Points Table", callback_data="ipl_table")],
            back_and_home_row(),
        ]),
    )


# ---------------------------------------------------------------------------
# 3. Predictions (existing)
# ---------------------------------------------------------------------------

async def ipl_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show upcoming IPL matches with predict buttons."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    def _fetch():
        from scrapers.cricbuzz_schedule import get_upcoming_matches
        matches = get_upcoming_matches(days=14)
        ipl = [m for m in matches if "ipl" in (m.get("series_name") or "").lower()
               or "indian premier" in (m.get("series_name") or "").lower()]
        if not ipl:
            ipl = [m for m in matches if m.get("match_type") == "T20"]
        return ipl[:10]

    matches = await asyncio.to_thread(_fetch)

    if not matches:
        await q.edit_message_text(
            "\U0001f52e No upcoming IPL matches found.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    rows = []
    for m in matches:
        t1, t2 = m["team1"], m["team2"]
        cid = m["cricbuzz_match_id"]
        label = f"\U0001f52e {t1} vs {t2}"
        if len(label) > 50:
            label = f"\U0001f52e {t1[:15]} vs {t2[:15]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"predict_match|{cid}")])
    rows.append(back_and_home_row())

    await q.edit_message_text(
        "\U0001f52e *IPL Predictions*\n\nTap a match to predict:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )


# ---------------------------------------------------------------------------
# 4. Team Rankings (existing)
# ---------------------------------------------------------------------------

async def ipl_team_rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show IPL franchise strength rankings."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    await q.edit_message_text("\u23f3 Computing franchise rankings...")

    def _run():
        from features.ipl_features import get_franchise_strength
        teams = _get_canonical_teams()
        rankings = []
        for team in teams:
            try:
                strength = get_franchise_strength(team)
            except Exception:
                strength = 50.0
            rankings.append({"team": team, "strength": strength})
        rankings.sort(key=lambda x: x["strength"], reverse=True)
        return rankings

    rankings = await asyncio.to_thread(_run)

    lines = [
        "\U0001f3c5 IPL FRANCHISE RANKINGS",
        "",
        f"  {'#':<3} {'Team':<28} Strength",
        "  " + "\u2500" * 42,
    ]
    for i, r in enumerate(rankings, 1):
        team = r["team"]
        s = r["strength"]
        bar_len = max(0, int(s / 100 * 12))
        block = "\u2588" * bar_len
        lines.append(f"  {i:<3} {team:<28} {s:.1f}  {block}")

    await q.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
    )


# ---------------------------------------------------------------------------
# 5. Browse Teams (NEW)
# ---------------------------------------------------------------------------

async def ipl_teams_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all 10 IPL teams as buttons."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    teams = _get_canonical_teams()
    context.user_data["ipl_teams"] = teams

    rows = []
    # Two teams per row for a compact grid
    for i in range(0, len(teams), 2):
        row = [InlineKeyboardButton(teams[i], callback_data=f"ipl_td|{i}")]
        if i + 1 < len(teams):
            row.append(InlineKeyboardButton(teams[i + 1], callback_data=f"ipl_td|{i + 1}"))
        rows.append(row)
    rows.append(back_and_home_row())

    await q.edit_message_text(
        "\U0001f3cf *IPL Teams*\n\nSelect a team to view details:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )


# ---------------------------------------------------------------------------
# 6. Team Detail Card (NEW)
# ---------------------------------------------------------------------------

async def ipl_team_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a rich team card: strength, form, home ground, points table entry."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl_teams")

    # Parse team index from callback data
    try:
        idx = int(q.data.split("|")[1])
    except (IndexError, ValueError):
        await q.edit_message_text("Invalid team selection.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    teams = context.user_data.get("ipl_teams") or _get_canonical_teams()
    if idx < 0 or idx >= len(teams):
        await q.edit_message_text("Team not found.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    team = teams[idx]
    await q.edit_message_text(f"\u23f3 Loading {team}...")

    def _run():
        from features.ipl_features import get_franchise_strength, get_ipl_team_form, IPL_HOME_GROUNDS
        from features.ipl_season import get_points_table

        strength = get_franchise_strength(team)
        form = get_ipl_team_form(team)
        home = IPL_HOME_GROUNDS.get(team, "Unknown")
        table = get_points_table()
        entry = None
        for t in table:
            if t["team"] == team:
                entry = t
                break
        return strength, form, home, entry

    strength, form, home, entry = await asyncio.to_thread(_run)

    form_tag = "\U0001f525 Hot" if form >= 70 else ("\u2744\ufe0f Cold" if form <= 30 else "\u27a1\ufe0f Neutral")

    lines = [
        f"\U0001f3cf {team}",
        "",
        f"\U0001f3df\ufe0f  Home:     {home}",
        f"\U0001f4aa  Strength: {bar(strength)}",
        f"\U0001f4c8  Form:     {bar(form)}  {form_tag}",
    ]

    if entry:
        lines += [
            "",
            "SEASON",
            f"  Played {entry['played']} | W {entry['won']} | L {entry['lost']} | Pts {entry['points']}",
            f"  Position: #{entry.get('position', '?')}  |  Win%: {entry.get('win_pct', 0):.1f}%",
        ]
    else:
        lines.append("\n  No season data found.")

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f465 Squad", callback_data=f"ipl_sq|{idx}"),
            InlineKeyboardButton("\U0001f4ca Stats", callback_data=f"ipl_ts|{idx}"),
            InlineKeyboardButton("\U0001f4c8 Form", callback_data=f"ipl_tf|{idx}"),
        ],
        [InlineKeyboardButton("\u2b05\ufe0f Teams", callback_data="ipl_teams")],
        back_and_home_row(),
    ])

    await q.edit_message_text("\n".join(lines), reply_markup=kb)


# ---------------------------------------------------------------------------
# 7. Squad Viewer (NEW)
# ---------------------------------------------------------------------------

async def ipl_squad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show team squad grouped by role with ratings."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl_team_detail")

    try:
        idx = int(q.data.split("|")[1])
    except (IndexError, ValueError):
        await q.edit_message_text("Invalid selection.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    teams = context.user_data.get("ipl_teams") or _get_canonical_teams()
    if idx < 0 or idx >= len(teams):
        await q.edit_message_text("Team not found.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    team = teams[idx]
    await q.edit_message_text(f"\u23f3 Loading squad for {team}...")

    def _run():
        from features.team_features import get_team_squad
        from ratings.player_ratings import get_player_rating
        from features.player_features import get_player_role

        squad = get_team_squad(team, "T20")
        players = []
        for p in squad:
            rating = get_player_rating(p, "T20")
            role = get_player_role(p, "T20")
            players.append({
                "name": p,
                "role": role,
                "overall": rating.get("overall_rating", 50),
                "batting": rating.get("batting_rating", 50),
                "bowling": rating.get("bowling_rating", 50),
                "form": rating.get("form_score", 50),
            })
        return players

    players = await asyncio.to_thread(_run)

    # Store players in context for the player profile handler
    context.user_data["ipl_squad_players"] = [p["name"] for p in players]

    # Group by role
    groups: dict[str, list] = {}
    for p in players:
        role = p["role"].capitalize() if p["role"] != "unknown" else "Other"
        groups.setdefault(role, []).append(p)

    # Sort within each group by overall rating descending
    for role in groups:
        groups[role].sort(key=lambda x: x["overall"], reverse=True)

    lines = [
        f"\U0001f465 SQUAD \u2014 {team}",
        f"  {len(players)} players",
        "",
    ]

    player_names = context.user_data["ipl_squad_players"]
    role_order = ["Batsman", "Allrounder", "Bowler", "Other"]
    for role in role_order:
        group = groups.get(role, [])
        if not group:
            continue
        lines.append(f"{_role_emoji(role)}  {role.upper()}S")
        for p in group:
            pidx = player_names.index(p["name"])
            name = p["name"]
            if len(name) > 20:
                name = name[:17] + "..."
            lines.append(
                f"  {name:<20} {p['overall']:5.1f}  "
                f"B{p['batting']:.0f} W{p['bowling']:.0f} F{p['form']:.0f}"
            )
        lines.append("")

    # Build player buttons (paginated)
    btn_rows = []
    for i in range(0, min(len(player_names), 20), 2):
        row = []
        p1 = player_names[i]
        label1 = p1 if len(p1) <= 22 else p1[:19] + "..."
        row.append(InlineKeyboardButton(label1, callback_data=f"ipl_pl|{i}"))
        if i + 1 < len(player_names):
            p2 = player_names[i + 1]
            label2 = p2 if len(p2) <= 22 else p2[:19] + "..."
            row.append(InlineKeyboardButton(label2, callback_data=f"ipl_pl|{i + 1}"))
        btn_rows.append(row)

    btn_rows.append([InlineKeyboardButton(f"\u2b05\ufe0f {team[:20]}", callback_data=f"ipl_td|{idx}")])
    btn_rows.append(back_and_home_row())

    await q.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(btn_rows),
    )


# ---------------------------------------------------------------------------
# 8. Player Profile (NEW)
# ---------------------------------------------------------------------------

async def ipl_player_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show individual player profile: rating, batting, bowling stats."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl_squad")

    try:
        pidx = int(q.data.split("|")[1])
    except (IndexError, ValueError):
        await q.edit_message_text("Invalid player selection.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    players = context.user_data.get("ipl_squad_players", [])
    if pidx < 0 or pidx >= len(players):
        await q.edit_message_text("Player not found.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    player = players[pidx]
    await q.edit_message_text(f"\u23f3 Loading profile for {player}...")

    def _run():
        from ratings.player_ratings import get_player_rating
        from features.player_features import get_batting_stats, get_bowling_stats, get_player_role

        rating = get_player_rating(player, "T20")
        batting = get_batting_stats(player, "T20")
        bowling = get_bowling_stats(player, "T20")
        role = get_player_role(player, "T20")
        rating["role"] = role
        return rating, batting, bowling

    rating, batting, bowling = await asyncio.to_thread(_run)
    text = format_player_profile(player, "T20", rating, batting, bowling)

    # Navigation: back to squad if we know the team index
    nav_rows = []
    ipl_teams = context.user_data.get("ipl_teams", [])
    # We don't store the team idx directly but can navigate back generically
    nav_rows.append(back_and_home_row())

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(nav_rows),
    )


# ---------------------------------------------------------------------------
# 9. Team Stats — H2H + Venue (NEW)
# ---------------------------------------------------------------------------

async def ipl_team_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show H2H records against other IPL teams and venue stats at home ground."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl_team_detail")

    try:
        idx = int(q.data.split("|")[1])
    except (IndexError, ValueError):
        await q.edit_message_text("Invalid selection.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    teams = context.user_data.get("ipl_teams") or _get_canonical_teams()
    if idx < 0 or idx >= len(teams):
        await q.edit_message_text("Team not found.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    team = teams[idx]
    await q.edit_message_text(f"\u23f3 Loading stats for {team}...")

    def _run():
        from features.ipl_features import get_ipl_h2h, IPL_HOME_GROUNDS
        from features.team_features import get_venue_win_rate

        others = [t for t in _get_canonical_teams() if t != team]
        h2h_records = []
        for opp in others:
            try:
                h2h = get_ipl_h2h(team, opp)
                if h2h["total"] > 0:
                    h2h_records.append({"opponent": opp, **h2h})
            except Exception:
                pass
        h2h_records.sort(key=lambda x: x["total"], reverse=True)

        home = IPL_HOME_GROUNDS.get(team, "")
        venue_wr = get_venue_win_rate(team, home, "T20") if home else 50.0
        return h2h_records, home, venue_wr

    h2h_records, home, venue_wr = await asyncio.to_thread(_run)

    lines = [
        f"\U0001f4ca STATS \u2014 {team}",
        "",
    ]

    # Venue stats
    if home:
        lines += [
            f"\U0001f3df\ufe0f  HOME VENUE: {home}",
            f"  Win rate: {venue_wr:.1f}%  {bar(venue_wr)}",
            "",
        ]

    # H2H
    lines.append("HEAD-TO-HEAD IN IPL")
    lines.append(f"  {'Opponent':<25} {'P':>3} {'W':>3} {'L':>3} {'Win%':>6}")
    lines.append("  " + "\u2500" * 44)

    for rec in h2h_records:
        opp = rec["opponent"]
        if len(opp) > 25:
            opp = opp[:22] + "..."
        wins = rec["team1_wins"]
        losses = rec["team2_wins"]
        total = rec["total"]
        pct = rec["team1_win_pct"]
        lines.append(f"  {opp:<25} {total:>3} {wins:>3} {losses:>3} {pct:>5.1f}%")

    if not h2h_records:
        lines.append("  No H2H data found.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"\u2b05\ufe0f {team[:20]}", callback_data=f"ipl_td|{idx}")],
        back_and_home_row(),
    ])

    await q.edit_message_text("\n".join(lines), reply_markup=kb)


# ---------------------------------------------------------------------------
# 10. Team Form Chart (NEW)
# ---------------------------------------------------------------------------

async def ipl_team_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last 10 IPL match results with W/L indicators."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl_team_detail")

    try:
        idx = int(q.data.split("|")[1])
    except (IndexError, ValueError):
        await q.edit_message_text("Invalid selection.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    teams = context.user_data.get("ipl_teams") or _get_canonical_teams()
    if idx < 0 or idx >= len(teams):
        await q.edit_message_text("Team not found.",
                                  reply_markup=InlineKeyboardMarkup([back_and_home_row()]))
        return

    team = teams[idx]
    await q.edit_message_text(f"\u23f3 Loading form for {team}...")

    def _run():
        from database.db import get_connection
        from features.ipl_features import get_ipl_team_form

        conn = get_connection()
        rows = conn.execute("""
            SELECT team1, team2, winner, date, venue, result_margin, result_type
            FROM matches
            WHERE competition = 'IPL' AND gender = 'male'
              AND (team1 = ? OR team2 = ?) AND winner IS NOT NULL
            ORDER BY date DESC LIMIT 10
        """, (team, team)).fetchall()
        conn.close()

        form_pct = get_ipl_team_form(team)
        return [dict(r) for r in rows], form_pct

    matches, form_pct = await asyncio.to_thread(_run)

    form_tag = "\U0001f525 Hot" if form_pct >= 70 else ("\u2744\ufe0f Cold" if form_pct <= 30 else "\u27a1\ufe0f Neutral")

    lines = [
        f"\U0001f4c8 FORM \u2014 {team}",
        f"  Weighted form: {form_pct:.1f}%  {form_tag}",
        "",
        "LAST 10 IPL MATCHES",
        "",
    ]

    if matches:
        wins = []
        for m in matches:
            is_win = m["winner"] == team
            wins.append(is_win)
            opponent = m["team2"] if m["team1"] == team else m["team1"]
            result_icon = "\u2705 W" if is_win else "\u274c L"
            margin = ""
            if m.get("result_margin") and m.get("result_type"):
                margin = f" by {m['result_margin']} {m['result_type']}"
            opp_short = opponent if len(opponent) <= 22 else opponent[:19] + "..."
            lines.append(f"  {result_icon}  vs {opp_short}{margin}")

        win_count = sum(wins)
        loss_count = len(wins) - win_count
        lines += [
            "",
            f"  Record: {win_count}W {loss_count}L  |  {_wl_indicator(wins)}",
        ]
    else:
        lines.append("  No recent IPL matches found.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"\u2b05\ufe0f {team[:20]}", callback_data=f"ipl_td|{idx}")],
        back_and_home_row(),
    ])

    await q.edit_message_text("\n".join(lines), reply_markup=kb)


# ---------------------------------------------------------------------------
# 11. Top IPL Players (NEW)
# ---------------------------------------------------------------------------

async def ipl_top_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top 20 T20 players who play in IPL."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    await q.edit_message_text("\u23f3 Loading top IPL players...")

    def _run():
        from database.db import get_connection
        from ratings.player_ratings import get_player_rating

        conn = get_connection()
        # Get distinct players who have played IPL recently, ordered by rating
        rows = conn.execute("""
            SELECT DISTINCT pms.player_name
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.id
            WHERE m.competition = 'IPL' AND m.gender = 'male'
            ORDER BY m.date DESC
            LIMIT 500
        """).fetchall()
        conn.close()

        seen = set()
        unique_names = []
        for r in rows:
            name = r["player_name"]
            if name not in seen:
                seen.add(name)
                unique_names.append(name)

        # Fetch ratings and sort
        rated = []
        for name in unique_names:
            rating = get_player_rating(name, "T20")
            if rating.get("games_played", 0) >= 5:
                rated.append(rating)

        rated.sort(key=lambda x: x.get("overall_rating", 0), reverse=True)
        return rated[:20]

    top = await asyncio.to_thread(_run)

    if not top:
        await q.edit_message_text(
            "No IPL player data available.",
            reply_markup=InlineKeyboardMarkup([back_and_home_row()]),
        )
        return

    # Store for player profile navigation
    context.user_data["ipl_squad_players"] = [p["player_name"] for p in top]

    lines = [
        "\u2b50 TOP 20 IPL PLAYERS (T20)",
        "",
        f"  {'#':<3} {'Player':<22} {'Ovr':>5} {'Bat':>5} {'Bowl':>5} {'Form':>5}",
        "  " + "\u2500" * 50,
    ]
    for i, p in enumerate(top, 1):
        name = p.get("player_name", "Unknown")
        if len(name) > 22:
            name = name[:19] + "..."
        lines.append(
            f"  {i:<3} {name:<22} {p.get('overall_rating', 0):5.1f} "
            f"{p.get('batting_rating', 0):5.1f} {p.get('bowling_rating', 0):5.1f} "
            f"{p.get('form_score', 0):5.1f}"
        )

    # Player buttons (up to 20)
    player_names = context.user_data["ipl_squad_players"]
    btn_rows = []
    for i in range(0, len(player_names), 2):
        row = []
        p1 = player_names[i]
        label1 = p1 if len(p1) <= 22 else p1[:19] + "..."
        row.append(InlineKeyboardButton(label1, callback_data=f"ipl_pl|{i}"))
        if i + 1 < len(player_names):
            p2 = player_names[i + 1]
            label2 = p2 if len(p2) <= 22 else p2[:19] + "..."
            row.append(InlineKeyboardButton(label2, callback_data=f"ipl_pl|{i + 1}"))
        btn_rows.append(row)

    btn_rows.append(back_and_home_row())

    await q.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(btn_rows),
    )


# ---------------------------------------------------------------------------
# 12. Season Overview (NEW)
# ---------------------------------------------------------------------------

async def ipl_season_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Combine points table + playoff probabilities + upcoming IPL matches."""
    q = update.callback_query
    await q.answer()
    context.user_data.setdefault("nav_stack", []).append("ipl")

    await q.edit_message_text("\u23f3 Building season overview...")

    def _run():
        from features.ipl_season import get_points_table, simulate_playoff_probabilities
        table = get_points_table()
        probs = simulate_playoff_probabilities()

        upcoming = []
        try:
            from scrapers.cricbuzz_schedule import get_upcoming_matches
            matches = get_upcoming_matches(days=14)
            upcoming = [m for m in matches if "ipl" in (m.get("series_name") or "").lower()
                        or "indian premier" in (m.get("series_name") or "").lower()]
            if not upcoming:
                upcoming = [m for m in matches if m.get("match_type") == "T20"]
            upcoming = upcoming[:5]
        except Exception:
            pass

        return table, probs, upcoming

    table, probs, upcoming = await asyncio.to_thread(_run)

    lines = [
        "\U0001f4c5 IPL SEASON OVERVIEW",
        "",
    ]

    # --- Mini points table (top 4 + bottom) ---
    if table:
        lines.append("STANDINGS (Top 4 highlighted)")
        lines.append(f"  {'#':<3} {'Team':<25} {'P':>3} {'W':>3} {'Pts':>4}")
        lines.append("  " + "\u2500" * 42)
        for i, t in enumerate(table):
            team = t["team"]
            if len(team) > 25:
                team = team[:22] + "..."
            marker = " \u2b50" if i < 4 else ""
            lines.append(
                f"  {i + 1:<3} {team:<25} {t['played']:>3} {t['won']:>3} {t['points']:>4}{marker}"
            )
        lines.append("")

    # --- Playoff probabilities (top contenders) ---
    if probs:
        lines.append("PLAYOFF PROBABILITIES")
        top_contenders = [p for p in probs if p.get("playoff_prob", 0) > 5]
        for p in top_contenders[:6]:
            team = p["team"]
            if len(team) > 22:
                team = team[:19] + "..."
            prob = p.get("playoff_prob", 0)
            bar_len = max(0, int(prob / 100 * 12))
            block = "\u2588" * bar_len
            lines.append(f"  {team:<22} {prob:5.1f}% {block}")
        lines.append("")

    # --- Upcoming matches ---
    if upcoming:
        lines.append("UPCOMING MATCHES")
        for m in upcoming:
            t1 = m.get("team1", "?")
            t2 = m.get("team2", "?")
            start_time = m.get("start_time", "")
            date_str = ""
            if start_time:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00").replace("+00:00", "")
                    )
                    date_str = f" \u2022 {dt.strftime('%b %d')}"
                except (ValueError, TypeError):
                    pass
            lines.append(f"  \U0001f3cf {t1} vs {t2}{date_str}")
    else:
        lines.append("No upcoming IPL matches found.")

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f4ca Full Table", callback_data="ipl_table"),
            InlineKeyboardButton("\U0001f3b2 Full Odds", callback_data="ipl_playoffs"),
        ],
        [
            InlineKeyboardButton("\U0001f3cf Browse Teams", callback_data="ipl_teams"),
            InlineKeyboardButton("\u2b50 Top Players", callback_data="ipl_top_players"),
        ],
        back_and_home_row(),
    ])

    await q.edit_message_text("\n".join(lines), reply_markup=kb)
