"""
frontend/bot/formatters.py
Rich text formatters for Telegram bot messages.
Friendly, emoji-rich, zero jargon.
"""
from __future__ import annotations

import json


# ─── helpers ────────────────────────────────────────────────────────────

def bar(score: float, width: int = 14) -> str:
    """Pretty progress bar visualization."""
    score = max(0, min(100, score))
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled) + f" {score:.0f}"


def _prob_bar(team: str, pct: float, width: int = 15) -> str:
    """Visual probability bar: *India*  ████████████░░░  78%"""
    pct = max(0, min(100, pct))
    filled = int(pct / 100 * width)
    return f"  *{team}*  {'█' * filled + '░' * (width - filled)}  {pct:.0f}%"


def _tier_label(rating: float) -> str:
    """Human-readable tier label for a player rating."""
    if rating >= 80:
        return "🌟 Elite"
    if rating >= 65:
        return "💪 Strong"
    if rating >= 50:
        return "👍 Average"
    return "🌱 Developing"


def _model_display(key: str) -> str:
    """Friendly model names — no tech jargon."""
    return {
        "elo_prob": "📊 Rating System",
        "lr_prob":  "📈 Stats Model",
        "xgb_prob": "🤖 AI Model",
        "mc_prob":  "🎲 Simulation",
    }.get(key, key)


def _role_emoji(role: str) -> str:
    """Emoji for cricket role."""
    r = (role or "").upper()[:3]
    if r in ("BAT",):
        return "🏏"
    if r in ("BOW",):
        return "⚾"
    if r in ("AR", "ALL"):
        return "⭐"
    if r in ("WK",):
        return "🧤"
    return "🏏"


# ─── predictions ────────────────────────────────────────────────────────

def format_prediction(team1: str, team2: str, fmt: str, result: dict) -> str:
    """Format ensemble prediction — friendly, visual, plain-English."""
    final = result.get("ensemble_prob", 50.0)
    margin = abs(final - 50)

    # Confidence label
    if margin >= 15:
        conf = "🟢 Very confident pick!"
    elif margin >= 7:
        conf = "🟡 Slight edge"
    else:
        conf = "🔴 Coin flip — could go either way!"

    # Verdict sentence
    leader = team1 if final >= 50 else team2
    if margin >= 15:
        verdict = f"*{leader}* hold a clear advantage heading into this one! 🔥"
    elif margin >= 7:
        verdict = f"*{leader}* have a slim edge, but don't count the other side out."
    else:
        verdict = "This is too close to call — expect a thriller! 🍿"

    lines = [
        f"🏏  *{team1} vs {team2}*  —  {fmt}",
        "",
        verdict,
        "",
        "━━━  Our Prediction  ━━━",
        "",
        _prob_bar(team1, final),
        _prob_bar(team2, 100 - final),
        "",
        f"Confidence: {conf}",
        "",
        "━━━  How the models see it  ━━━",
        "",
    ]

    model_keys = [
        ("elo_prob",  "elo1", "elo2"),
        ("lr_prob",   None,   None),
        ("xgb_prob",  None,   None),
        ("mc_prob",   None,   None),
    ]

    for key, r1, r2 in model_keys:
        if key in result:
            name = _model_display(key)
            val = result[key]
            extra = ""
            if r1 and r1 in result and r2 and r2 in result:
                extra = f"  (Ratings: {result[r1]:.0f} vs {result[r2]:.0f})"
            lines.append(f"  {name:<20} {val:.1f}%{extra}")

    lines += [
        "  ─────────────────────",
        f"  🏆 *Combined*{' ' * 10}{final:.1f}%",
    ]

    # Head-to-head
    h2h = result.get("h2h")
    if h2h and h2h.get("total", 0) > 0:
        lines += [
            "",
            f"🤝  *Head-to-Head*  ({h2h['total']} matches)",
            f"  {team1}: {h2h['team1_wins']} wins ({h2h['team1_win_pct']:.0f}%)",
            f"  {team2}: {h2h['team2_wins']} wins",
        ]

    # Recent form
    form1 = result.get("form1")
    form2 = result.get("form2")
    if form1 is not None and form2 is not None:
        lines += [
            "",
            "📅  *Recent Form*  (last 10 matches)",
            f"  {team1}: {form1:.0f}% wins",
            f"  {team2}: {form2:.0f}% wins",
        ]

    return "\n".join(lines)


# ─── Dream11 ────────────────────────────────────────────────────────────

def format_dream11_team(result: dict) -> str:
    """Format Dream11 fantasy team — friendly and clear."""
    if not result or not result.get("team"):
        return "❌ Couldn't build a Dream11 team — not enough player data right now."

    captain = result.get("captain", "")
    vc = result.get("vice_captain", "")
    total_credits = result.get("total_credits", 0)
    total_pts = result.get("total_expected_points", 0)

    lines = [
        "🎯  *Your Dream11 Team*",
        "",
        f"💰 Credits used: *{total_credits:.1f} / 100*",
        f"📈 Expected points: *{total_pts:.1f}*",
        "⚡ Built by AI optimizer",
        "",
    ]

    # Group by role
    roles_order = ["WK", "BAT", "AR", "BOWL"]
    grouped: dict[str, list] = {r: [] for r in roles_order}
    for p in result["team"]:
        role = (p.get("role", "BAT") or "BAT").upper()[:4]
        bucket = "BAT"
        for r in roles_order:
            if role.startswith(r[:2]):
                bucket = r
                break
        grouped[bucket].append(p)

    for role_key in roles_order:
        players = grouped.get(role_key, [])
        if not players:
            continue
        emoji = _role_emoji(role_key)
        role_label = {
            "WK": "Wicket-Keeper", "BAT": "Batters",
            "AR": "All-Rounders", "BOWL": "Bowlers",
        }.get(role_key, role_key)
        lines.append(f"{emoji}  *{role_label}*")

        for p in players:
            name = p.get("name", p.get("player_name", "Unknown"))
            credits = p.get("credits", 0)
            pts = p.get("expected_points", 0)
            tag = ""
            if name == captain:
                tag = "  👑 C"
            elif name == vc:
                tag = "  🥈 VC"

            if len(name) > 22:
                name = name[:19] + "..."
            lines.append(f"  {name:<22}  {credits:.1f} Cr  |  {pts:.1f} pts{tag}")

        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━",
        f"👑  *Captain:*  {captain}  (2x points)",
        f"🥈  *Vice-Captain:*  {vc}  (1.5x points)",
    ]

    return "\n".join(lines)


# ─── match card ─────────────────────────────────────────────────────────

def format_match_card(match: dict) -> str:
    """Format upcoming match detail card — clean & emoji-rich."""
    team1 = match.get("team1", "TBD")
    team2 = match.get("team2", "TBD")
    venue = match.get("venue", "TBD")
    series = match.get("series_name", "")
    fmt = match.get("match_type", "T20")
    start_time = match.get("start_time", "")

    date_str = "TBD"
    if start_time:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(
                start_time.replace("Z", "+00:00").replace("+00:00", ""))
            date_str = dt.strftime("%A, %d %b %Y · %I:%M %p")
        except (ValueError, TypeError):
            date_str = start_time

    lines = [
        f"🏏  *{team1} vs {team2}*",
        "",
    ]

    if series:
        lines.append(f"🏆  {series}")
    lines += [
        f"🎮  Format: {fmt}",
        f"🏟  Venue: {venue}",
        f"📅  {date_str}",
    ]

    xi1 = match.get("playing_xi_team1", [])
    xi2 = match.get("playing_xi_team2", [])

    if xi1:
        lines += ["", f"📋  *Playing XI — {team1}*"]
        for i, p in enumerate(xi1, 1):
            lines.append(f"  {i:>2}. {p}")

    if xi2:
        lines += ["", f"📋  *Playing XI — {team2}*"]
        for i, p in enumerate(xi2, 1):
            lines.append(f"  {i:>2}. {p}")

    if not xi1 and not xi2:
        lines.append(
            "\n⏳ Playing XI not announced yet — check back closer to the match!")

    return "\n".join(lines)


# ─── player profile ────────────────────────────────────────────────────

def format_player_profile(player: str, fmt: str, rating: dict,
                          batting: dict, bowling: dict) -> str:
    """Format player profile with ratings, tiers, and career stats."""
    role = rating.get("role", "Unknown")
    games = rating.get("games_played", 0)
    overall = rating.get("overall_rating", 50)

    lines = [
        f"{_role_emoji(role)}  *{player}*  —  {fmt} {role}",
        f"🎮 {games} matches  |  {_tier_label(overall)}",
        "",
        "━━━  Player Ratings  ━━━",
        "",
        f"  🏆 Overall      {bar(overall)}",
        f"  🏏 Batting      {bar(rating.get('batting_rating', 50))}",
        f"  ⚾ Bowling      {bar(rating.get('bowling_rating', 50))}",
        f"  🔥 Form         {bar(rating.get('form_score', 50))}",
        f"  📊 Consistency  {bar(rating.get('consistency', 50))}",
    ]

    if batting and batting.get("innings", 0) > 0:
        lines += [
            "",
            "🏏  *Career Batting*",
            f"  Innings: {batting['innings']}  ·  Runs: {batting.get('total_runs', 0):,}",
            f"  Average: {batting.get('average', 0):.2f}  ·  "
            f"Strike Rate: {batting.get('strike_rate', 0):.2f}",
            f"  Highest: {batting.get('highest', 0)}  ·  "
            f"50s: {batting.get('fifties', 0)}  ·  100s: {batting.get('hundreds', 0)}",
        ]

    if bowling and bowling.get("total_wickets", 0) > 0:
        lines += [
            "",
            "⚾  *Career Bowling*",
            f"  Wickets: {bowling['total_wickets']}  ·  "
            f"Overs: {bowling.get('total_overs', 0):.1f}",
            f"  Economy: {bowling.get('economy', 0):.2f}  ·  "
            f"Average: {bowling.get('bowling_average', 0):.2f}",
            f"  Strike Rate: {bowling.get('bowling_strike_rate', 0):.1f}  ·  "
            f"Dot%: {bowling.get('dot_pct', 0):.1f}%",
        ]

    return "\n".join(lines)


# ─── points table ──────────────────────────────────────────────────────

def format_points_table(table: list) -> str:
    """Format IPL points table — medals for top 3, qualifier zone line."""
    if not table:
        return "📊 No points table data yet — the season might not have started!"

    lines = [
        "📊  *IPL Points Table*",
        "",
        f"  {'#':<3} {'Team':<25} {'M':>3} {'W':>3} {'L':>3} {'Pts':>4} {'NRR':>7}",
        "  " + "─" * 53,
    ]

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for i, t in enumerate(table, 1):
        team = t.get("team", "Unknown")
        if len(team) > 25:
            team = team[:22] + "..."
        matches = t.get("matches", t.get("played", 0))
        wins = t.get("wins", t.get("won", 0))
        losses = t.get("losses", t.get("lost", 0))
        pts = t.get("points", 0)
        nrr = t.get("nrr", t.get("net_run_rate", 0))

        medal = medals.get(i, "  ")
        prefix = f"{medal}" if i <= 3 else "  "

        line = (f"{prefix}{i:<3} {team:<25} "
                f"{matches:>3} {wins:>3} {losses:>3} {pts:>4} {nrr:>+7.3f}")
        lines.append(line)

        # Qualifier zone separator after position 4
        if i == 4:
            lines.append("  " + "- " * 27 + "  ✅ Top 4 qualify")

    return "\n".join(lines)


# ─── playoff probabilities ─────────────────────────────────────────────

def format_playoff_probs(results: list) -> str:
    """Format playoff qualification odds — plain English + colour indicators."""
    if not results:
        return "🎲 No playoff simulation data yet — check back after a few matches!"

    lines = [
        "🎲  *Playoff Chances*",
        "How likely is each team to make the playoffs?",
        "",
        f"  {'Team':<25} {'Qualify':>8}  {'Top 2':>8}  Outlook",
        "  " + "─" * 60,
    ]

    for r in results:
        team = r.get("team", "Unknown")
        if len(team) > 25:
            team = team[:22] + "..."
        qualify = r.get("qualify_pct", r.get("playoff_prob", 0))
        top2 = r.get("top2_pct", r.get("top2_prob", 0))

        # Colour indicator + plain English
        if qualify >= 80:
            indicator = "🟢 Almost certain"
        elif qualify >= 40:
            indicator = "🟡 Good chance"
        else:
            indicator = "🔴 Slim chance"

        lines.append(
            f"  {team:<25} {qualify:>7.1f}%  {top2:>7.1f}%  {indicator}")

    return "\n".join(lines)


# ─── team analysis ─────────────────────────────────────────────────────

def format_team_analysis(team: str, fmt: str, elo: float, form: float,
                         squad: list, ratings: list) -> str:
    """Format team analysis — friendly language with a verdict."""
    if form >= 70:
        form_tag = "🔥 On fire!"
    elif form <= 30:
        form_tag = "❄️ Struggling"
    else:
        form_tag = "➡️ Steady"

    lines = [
        f"🏏  *{team}*  —  {fmt} Analysis",
        "",
        "━━━  Team Overview  ━━━",
        "",
        f"  📊 Team Rating:  *{elo:.0f}*",
        f"  📅 Recent Form:  *{form:.0f}%* wins (last 10)  {form_tag}",
    ]

    if ratings:
        avg_rat = sum(r.get("overall_rating", 50) for r in ratings) / len(ratings)
        sorted_r = sorted(
            ratings, key=lambda x: x.get("overall_rating", 0), reverse=True)
        top_bat = sorted(
            ratings, key=lambda x: x.get("batting_rating", 0), reverse=True)[:3]
        top_bwl = sorted(
            ratings, key=lambda x: x.get("bowling_rating", 0), reverse=True)[:3]

        lines += [
            "",
            f"━━━  Squad Strength  ━━━  (avg rating: {avg_rat:.0f}/100)",
            "",
        ]

        for r in sorted_r:
            name = r.get("player_name", "Unknown")
            role = r.get("role", "")
            emoji = _role_emoji(role)
            ovr = r.get("overall_rating", 0)
            tier = _tier_label(ovr)
            form_s = r.get("form_score", 0)
            if len(name) > 20:
                name = name[:17] + "..."
            lines.append(
                f"  {emoji} {name:<20}  {bar(ovr)}  "
                f"Form: {form_s:.0f}  {tier}"
            )

        lines += [
            "",
            "⭐  *Key Players*",
            f"  🏏 Best batters:  "
            f"{', '.join(r.get('player_name', '?') for r in top_bat)}",
            f"  ⚾ Best bowlers:  "
            f"{', '.join(r.get('player_name', '?') for r in top_bwl)}",
            f"  🏆 Top overall:   "
            f"{', '.join(r.get('player_name', '?') for r in sorted_r[:3])}",
        ]

    # Verdict
    lines.append("")
    if form >= 70 and elo >= 1550:
        lines.append(
            "💬 *Verdict:* This team is firing on all cylinders "
            "— a real title contender! 🏆")
    elif form >= 50 and elo >= 1500:
        lines.append(
            "💬 *Verdict:* Solid side with room for improvement. "
            "Watch out for them on their day.")
    elif form <= 30:
        lines.append(
            "💬 *Verdict:* Tough patch — they'll need to turn things "
            "around quickly.")
    else:
        lines.append(
            "💬 *Verdict:* A competitive squad that can challenge "
            "anyone on a good day.")

    return "\n".join(lines)


# ─── live scorecard ────────────────────────────────────────────────────

def format_live_scorecard(scorecard: dict) -> str:
    """Format a live match scorecard — polished emojis."""
    if not scorecard:
        return "❌ Scorecard not available right now."

    team_a = scorecard.get("team_a", scorecard.get("team1", "Team A"))
    team_b = scorecard.get("team_b", scorecard.get("team2", "Team B"))
    status = scorecard.get("status", "Live")

    lines = [
        f"🔴  *LIVE  —  {team_a} vs {team_b}*",
        f"📡 {status}",
        "",
    ]

    for i, inn in enumerate(scorecard.get("innings", []), 1):
        team = inn.get("batting_team", f"Innings {i}")
        runs = inn.get("total_runs", 0)
        wkts = inn.get("total_wickets", 0)
        overs = inn.get("total_overs", 0)
        lines.append(f"  *{team}*: {runs}/{wkts}  ({overs} ov)")

        # Current batsmen
        batsmen = inn.get("current_batsmen", [])
        for b in batsmen:
            name = b.get("name", "")
            if name:
                striker = " 🔵" if b.get("on_strike") else ""
                lines.append(
                    f"    🏏 {name}: {b.get('runs', 0)} "
                    f"({b.get('balls', 0)}b){striker}")

        # Current bowler
        bowler = inn.get("current_bowler", {})
        if bowler.get("name"):
            lines.append(
                f"    ⚾ {bowler['name']}: "
                f"{bowler.get('wickets', 0)}/{bowler.get('runs', 0)} "
                f"({bowler.get('overs', 0)} ov)")

        lines.append("")

    if scorecard.get("score_summary"):
        lines.append("📌 " + scorecard["score_summary"])

    return "\n".join(lines)


# ─── Elo rankings ──────────────────────────────────────────────────────

def format_elo_rankings(rankings: list, fmt: str) -> str:
    """Format Elo team rankings — friendly header + visual bars."""
    if not rankings:
        return f"🏅 No team ranking data found for {fmt} yet."

    lines = [
        f"🏅  *Team Power Rankings*  —  {fmt}",
        "Who's the strongest team right now?",
        "",
    ]

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for i, r in enumerate(rankings, 1):
        team = r.get("team", r.get("team_name", "Unknown"))
        elo = r.get("elo", 1500)
        bar_len = max(0, int((elo - 1300) / 800 * 14))
        medal = medals.get(i, f"{i:>2}.")

        lines.append(
            f"  {medal} {team:<26}  {'█' * bar_len}  {elo:.0f}")

    return "\n".join(lines)


# ─── top players ───────────────────────────────────────────────────────

def format_top_players(players: list, fmt: str) -> str:
    """Format top players leaderboard — friendly and readable."""
    if not players:
        return f"⭐ No player data found for {fmt} yet."

    lines = [
        f"⭐  *Top 20 {fmt} Players*",
        "The best performers right now:",
        "",
    ]

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for i, p in enumerate(players, 1):
        name = p.get("player_name", "Unknown")
        role = p.get("role", "")
        emoji = _role_emoji(role)
        ovr = p.get("overall_rating", 0)
        form = p.get("form_score", 0)
        games = p.get("games_played", 0)
        tier = _tier_label(ovr)

        if len(name) > 22:
            name = name[:19] + "..."

        medal = medals.get(i, f"{i:>2}.")
        lines.append(
            f"  {medal} {emoji} {name:<22}  {bar(ovr)}  "
            f"Form: {form:.0f}  ({games}G)  {tier}"
        )

    return "\n".join(lines)


# ─── NEW: rich match report ────────────────────────────────────────────

def format_rich_match_report(match: dict, prediction: dict | None,
                             form1: float | None,
                             form2: float | None) -> str:
    """Full match preview shown when clicking an upcoming match.
    Shows: match info, venue, verdict, prediction bars, H2H,
    form comparison, playing XI if available."""
    team1 = match.get("team1", "TBD")
    team2 = match.get("team2", "TBD")
    venue = match.get("venue", "TBD")
    series = match.get("series_name", "")
    fmt = match.get("match_type", "T20")
    start_time = match.get("start_time", "")

    date_str = "TBD"
    if start_time:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(
                start_time.replace("Z", "+00:00").replace("+00:00", ""))
            date_str = dt.strftime("%A, %d %b %Y · %I:%M %p")
        except (ValueError, TypeError):
            date_str = start_time

    lines = [
        f"🏏  *{team1} vs {team2}*",
        "",
    ]
    if series:
        lines.append(f"🏆 {series}")
    lines += [
        f"🏟  {venue}",
        f"📅  {date_str}  ·  {fmt}",
    ]

    # Prediction section
    if prediction:
        prob = prediction.get("ensemble_prob", 50.0)
        margin = abs(prob - 50)

        leader = team1 if prob >= 50 else team2
        if margin >= 15:
            verdict = f"🔥 *{leader}* are the clear favourites here!"
        elif margin >= 7:
            verdict = (f"📊 *{leader}* have a slight edge, "
                       "but it's competitive.")
        else:
            verdict = "🍿 Too close to call — this could be a cracker!"

        lines += [
            "",
            "━━━  Match Verdict  ━━━",
            "",
            verdict,
            "",
            _prob_bar(team1, prob),
            _prob_bar(team2, 100 - prob),
        ]

        # H2H
        h2h = prediction.get("h2h")
        if h2h and h2h.get("total", 0) > 0:
            lines += [
                "",
                f"🤝  *Head-to-Head*  ({h2h['total']} matches)",
                f"  {team1}: {h2h['team1_wins']} wins  ·  "
                f"{team2}: {h2h['team2_wins']} wins",
            ]

    # Form comparison
    if form1 is not None and form2 is not None:
        lines += [
            "",
            "📅  *Recent Form*  (last 10)",
            f"  {team1}: {form1:.0f}% wins",
            f"  {team2}: {form2:.0f}% wins",
        ]

    # Playing XI
    xi1 = match.get("playing_xi_team1", [])
    xi2 = match.get("playing_xi_team2", [])

    if xi1 or xi2:
        if xi1:
            lines += ["", f"📋  *{team1} XI*"]
            for i, p in enumerate(xi1, 1):
                lines.append(f"  {i:>2}. {p}")
        if xi2:
            lines += ["", f"📋  *{team2} XI*"]
            for i, p in enumerate(xi2, 1):
                lines.append(f"  {i:>2}. {p}")
    else:
        lines.append("\n⏳ Playing XI not announced yet")

    return "\n".join(lines)


# ─── NEW: IPL team card ────────────────────────────────────────────────

def format_ipl_team_card(team: str, strength: float, form: float,
                         home_ground: str,
                         table_entry: dict | None) -> str:
    """IPL team profile card with emoji-rich display."""
    if form >= 70:
        form_tag = "🔥 On fire!"
    elif form <= 30:
        form_tag = "❄️ Cold streak"
    else:
        form_tag = "➡️ Steady"

    lines = [
        f"🏏  *{team}*",
        "",
        f"💪 Team Strength:  {bar(strength)}  {_tier_label(strength)}",
        f"📅 Recent Form:    {form:.0f}%  {form_tag}",
        f"🏟  Home Ground:   {home_ground or 'TBD'}",
    ]

    if table_entry:
        matches = table_entry.get("matches", table_entry.get("played", 0))
        wins = table_entry.get("wins", table_entry.get("won", 0))
        losses = table_entry.get("losses", table_entry.get("lost", 0))
        pts = table_entry.get("points", 0)
        nrr = table_entry.get("nrr", table_entry.get("net_run_rate", 0))
        pos = table_entry.get("position", "?")

        lines += [
            "",
            "📊  *Season Record*",
            f"  Position: #{pos}  ·  Points: {pts}",
            f"  Played: {matches}  ·  Won: {wins}  ·  Lost: {losses}",
            f"  Net Run Rate: {nrr:+.3f}",
        ]

    return "\n".join(lines)


# ─── NEW: IPL squad view ──────────────────────────────────────────────

def format_ipl_squad(team: str, players_with_ratings: list) -> str:
    """Squad view grouped by role (BAT/BOWL/AR/WK) with ratings."""
    if not players_with_ratings:
        return f"📋 No squad data available for *{team}* yet."

    lines = [
        f"📋  *{team} — Full Squad*",
        "",
    ]

    roles_order = [
        ("WK",   "🧤 Wicket-Keepers"),
        ("BAT",  "🏏 Batters"),
        ("AR",   "⭐ All-Rounders"),
        ("BOWL", "⚾ Bowlers"),
    ]

    grouped: dict[str, list] = {r: [] for r, _ in roles_order}
    for p in players_with_ratings:
        role = (p.get("role", "BAT") or "BAT").upper()[:3]
        bucket = "BAT"
        for key, _ in roles_order:
            if role.startswith(key[:2]):
                bucket = key
                break
        grouped[bucket].append(p)

    for role_key, role_header in roles_order:
        players = grouped.get(role_key, [])
        if not players:
            continue
        # Sort by overall rating descending
        players = sorted(
            players, key=lambda x: x.get("overall_rating", 0), reverse=True)

        lines.append(f"*{role_header}*")
        for p in players:
            name = p.get("player_name", p.get("name", "Unknown"))
            ovr = p.get("overall_rating", 0)
            form_score = p.get("form_score", 0)
            tier = _tier_label(ovr)
            if len(name) > 22:
                name = name[:19] + "..."
            lines.append(
                f"  {name:<22}  {bar(ovr)}  "
                f"Form: {form_score:.0f}  {tier}")
        lines.append("")

    return "\n".join(lines)


# ─── NEW: IPL season overview ─────────────────────────────────────────

def format_ipl_season_overview(table: list, playoff_probs: list,
                               upcoming: list) -> str:
    """Season narrative summary — combines table, playoff odds, and
    upcoming fixtures into a single friendly overview."""
    lines = [
        "🏆  *IPL Season Overview*",
        "",
    ]

    # Top of the table
    if table:
        leader = table[0]
        leader_name = leader.get("team", "Unknown")
        leader_pts = leader.get("points", 0)
        lines += [
            "📊  *Standings Snapshot*",
            f"  🥇 {leader_name} lead the table with {leader_pts} points",
        ]
        for i, t in enumerate(table[:4], 1):
            team_name = t.get("team", "Unknown")
            pts = t.get("points", 0)
            wins = t.get("wins", t.get("won", 0))
            losses = t.get("losses", t.get("lost", 0))
            lines.append(
                f"  {i}. {team_name}  —  {pts} pts ({wins}W, {losses}L)")
        if len(table) > 4:
            bottom = table[-1]
            lines.append(
                f"  ...{len(table)}. {bottom.get('team', '?')}  —  "
                f"{bottom.get('points', 0)} pts")
        lines.append("")

    # Playoff picture
    if playoff_probs:
        lines.append("🎲  *Playoff Picture*")
        for r in playoff_probs[:4]:
            team_name = r.get("team", "Unknown")
            qualify = r.get("qualify_pct", r.get("playoff_prob", 0))
            if qualify >= 80:
                tag = "🟢 Almost certain"
            elif qualify >= 40:
                tag = "🟡 In the mix"
            else:
                tag = "🔴 Needs a miracle"
            lines.append(f"  {team_name}: {qualify:.0f}%  {tag}")

        # Danger zone
        long_shots = [
            r for r in playoff_probs
            if r.get("qualify_pct", r.get("playoff_prob", 0)) < 10
        ]
        if long_shots:
            names = ", ".join(r.get("team", "?") for r in long_shots[:3])
            lines.append(f"  ⚠️  Danger zone: {names}")
        lines.append("")

    # Upcoming matches
    if upcoming:
        lines.append("📅  *Coming Up Next*")
        for m in upcoming[:3]:
            t1 = m.get("team1", "?")
            t2 = m.get("team2", "?")
            start_time = m.get("start_time", "")
            day_str = ""
            if start_time:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                        .replace("+00:00", ""))
                    day_str = f"  ·  {dt.strftime('%a %d %b, %H:%M')}"
                except (ValueError, TypeError):
                    pass
            lines.append(f"  🏏 {t1} vs {t2}{day_str}")
        lines.append("")

    return "\n".join(lines)
