"""
frontend/bot/formatters.py
Rich text formatters for Telegram bot messages.
"""
import json


def bar(score: float, width: int = 14) -> str:
    """Progress bar visualization."""
    score = max(0, min(100, score))
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled) + f" {score:.0f}"


def format_prediction(team1: str, team2: str, fmt: str, result: dict) -> str:
    """Format ensemble prediction with model breakdown."""
    final = result.get("ensemble_prob", 50.0)
    margin = abs(final - 50)
    conf = "HIGH ★★★" if margin >= 15 else ("MEDIUM ★★☆" if margin >= 7 else "LOW ★☆☆")

    lines = [
        f"🏏 {team1} vs {team2} — {fmt}",
        "",
        "PREDICTION",
        f"  {team1}: {final:.1f}%",
        f"  {team2}: {100 - final:.1f}%",
        f"  Confidence: {conf}",
        "",
        "MODEL BREAKDOWN",
    ]

    if "elo_prob" in result:
        elo1 = result.get("elo1", 1500)
        elo2 = result.get("elo2", 1500)
        lines.append(f"  Elo          {result['elo_prob']:.1f}%  ({elo1:.0f} vs {elo2:.0f})")
    if "lr_prob" in result:
        lines.append(f"  Logistic     {result['lr_prob']:.1f}%")
    if "xgb_prob" in result:
        lines.append(f"  XGBoost      {result['xgb_prob']:.1f}%")
    if "mc_prob" in result:
        lines.append(f"  Monte Carlo  {result['mc_prob']:.1f}%")

    lines += [
        "  ─────────────────────",
        f"  Ensemble     {final:.1f}%",
    ]

    h2h = result.get("h2h")
    if h2h and h2h.get("total", 0) > 0:
        lines += [
            "",
            f"HEAD-TO-HEAD ({h2h['total']} matches)",
            f"  {team1}: {h2h['team1_wins']} wins ({h2h['team1_win_pct']:.0f}%)",
            f"  {team2}: {h2h['team2_wins']} wins",
        ]

    form1 = result.get("form1")
    form2 = result.get("form2")
    if form1 is not None and form2 is not None:
        lines += [
            "",
            "RECENT FORM (last 10)",
            f"  {team1}: {form1:.0f}%",
            f"  {team2}: {form2:.0f}%",
        ]

    return "\n".join(lines)


def format_dream11_team(result: dict) -> str:
    """Format Dream11 fantasy team."""
    if not result or not result.get("team"):
        return "❌ Could not generate Dream11 team. Not enough player data."

    captain = result.get("captain", "")
    vc = result.get("vice_captain", "")
    total_credits = result.get("total_credits", 0)
    total_pts = result.get("total_expected_points", 0)
    method = result.get("method", "unknown")

    lines = [
        "🎯 DREAM11 TEAM",
        f"Credits: {total_credits:.1f}/100  |  Exp. Points: {total_pts:.1f}",
        f"Method: {method}",
        "",
        f"  {'Player':<22} {'Role':<5} {'Cr':>4} {'Pts':>5}  Tag",
        "  " + "─" * 50,
    ]

    for p in result["team"]:
        name = p.get("name", p.get("player_name", "Unknown"))
        role = p.get("role", "?")[:4]
        credits = p.get("credits", 0)
        pts = p.get("expected_points", 0)
        tag = ""
        if name == captain:
            tag = " (C)"
        elif name == vc:
            tag = " (VC)"

        if len(name) > 22:
            name = name[:19] + "..."
        lines.append(f"  {name:<22} {role:<5} {credits:>4.1f} {pts:>5.1f}{tag}")

    lines += [
        "",
        f"  Captain:      {captain} (2x points)",
        f"  Vice-Captain: {vc} (1.5x points)",
    ]

    return "\n".join(lines)


def format_match_card(match: dict) -> str:
    """Format upcoming match detail card."""
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
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00").replace("+00:00", ""))
            date_str = dt.strftime("%a, %b %d %Y · %H:%M")
        except (ValueError, TypeError):
            date_str = start_time

    lines = [
        f"🏏 {team1} vs {team2}",
        "",
    ]

    if series:
        lines.append(f"Series: {series}")
    lines += [
        f"Format: {fmt}",
        f"Venue:  {venue}",
        f"Date:   {date_str}",
    ]

    xi1 = match.get("playing_xi_team1", [])
    xi2 = match.get("playing_xi_team2", [])

    if xi1:
        lines += ["", f"Playing XI — {team1}"]
        for i, p in enumerate(xi1, 1):
            lines.append(f"  {i:>2}. {p}")

    if xi2:
        lines += ["", f"Playing XI — {team2}"]
        for i, p in enumerate(xi2, 1):
            lines.append(f"  {i:>2}. {p}")

    if not xi1 and not xi2:
        lines.append("\nPlaying XI not yet announced")

    return "\n".join(lines)


def format_player_profile(player: str, fmt: str, rating: dict,
                          batting: dict, bowling: dict) -> str:
    """Format player profile with ratings and stats."""
    role = rating.get("role", "Unknown")
    games = rating.get("games_played", 0)

    lines = [
        f"🏏 {player} — {fmt} | {role}",
        f"Games: {games}",
        "",
        "RATINGS",
        f"  Overall     {bar(rating.get('overall_rating', 50))}",
        f"  Batting     {bar(rating.get('batting_rating', 50))}",
        f"  Bowling     {bar(rating.get('bowling_rating', 50))}",
        f"  Form        {bar(rating.get('form_score', 50))}",
        f"  Consistency {bar(rating.get('consistency', 50))}",
    ]

    if batting and batting.get("innings", 0) > 0:
        lines += [
            "",
            "CAREER BATTING",
            f"  Innings: {batting['innings']}  |  Runs: {batting.get('total_runs', 0):,}",
            f"  Average: {batting.get('average', 0):.2f}  |  SR: {batting.get('strike_rate', 0):.2f}",
            f"  Highest: {batting.get('highest', 0)}  |  50s: {batting.get('fifties', 0)}  |  100s: {batting.get('hundreds', 0)}",
        ]

    if bowling and bowling.get("total_wickets", 0) > 0:
        lines += [
            "",
            "CAREER BOWLING",
            f"  Wickets: {bowling['total_wickets']}  |  Overs: {bowling.get('total_overs', 0):.1f}",
            f"  Economy: {bowling.get('economy', 0):.2f}  |  Avg: {bowling.get('bowling_average', 0):.2f}",
            f"  SR: {bowling.get('bowling_strike_rate', 0):.1f}  |  Dot%: {bowling.get('dot_pct', 0):.1f}%",
        ]

    return "\n".join(lines)


def format_points_table(table: list) -> str:
    """Format IPL points table."""
    if not table:
        return "📊 No points table data available."

    lines = [
        "📊 IPL POINTS TABLE",
        "",
        f"  {'#':<3} {'Team':<25} {'M':>3} {'W':>3} {'L':>3} {'Pts':>4} {'NRR':>6}",
        "  " + "─" * 52,
    ]

    for i, t in enumerate(table, 1):
        team = t.get("team", "Unknown")
        if len(team) > 25:
            team = team[:22] + "..."
        matches = t.get("matches", t.get("played", 0))
        wins = t.get("wins", t.get("won", 0))
        losses = t.get("losses", t.get("lost", 0))
        pts = t.get("points", 0)
        nrr = t.get("nrr", t.get("net_run_rate", 0))

        lines.append(
            f"  {i:<3} {team:<25} {matches:>3} {wins:>3} {losses:>3} {pts:>4} {nrr:>+6.3f}"
        )

    return "\n".join(lines)


def format_playoff_probs(results: list) -> str:
    """Format playoff qualification probabilities."""
    if not results:
        return "🎲 No playoff simulation data available."

    lines = [
        "🎲 PLAYOFF PROBABILITIES",
        f"  (Monte Carlo simulation)",
        "",
        f"  {'Team':<25} {'Qualify':>8} {'Top 2':>8}",
        "  " + "─" * 45,
    ]

    for r in results:
        team = r.get("team", "Unknown")
        if len(team) > 25:
            team = team[:22] + "..."
        qualify = r.get("qualify_pct", r.get("playoff_prob", 0))
        top2 = r.get("top2_pct", r.get("top2_prob", 0))

        lines.append(f"  {team:<25} {qualify:>7.1f}% {top2:>7.1f}%")

    return "\n".join(lines)


def format_team_analysis(team: str, fmt: str, elo: float, form: float,
                         squad: list, ratings: list) -> str:
    """Format team analysis."""
    form_tag = "🔥 Hot" if form >= 70 else ("❄️ Cold" if form <= 30 else "➡️ Neutral")
    lines = [
        f"TEAM ANALYSIS — {team} ({fmt})",
        "",
        "OVERVIEW",
        f"  Elo Rating:     {elo:.1f}",
        f"  Form (last 10): {form:.1f}%  {form_tag}",
    ]

    if ratings:
        avg_rat = sum(r.get("overall_rating", 50) for r in ratings) / len(ratings)
        sorted_r = sorted(ratings, key=lambda x: x.get("overall_rating", 0), reverse=True)
        top_bat = sorted(ratings, key=lambda x: x.get("batting_rating", 0), reverse=True)[:3]
        top_bwl = sorted(ratings, key=lambda x: x.get("bowling_rating", 0), reverse=True)[:3]

        lines += [
            "",
            f"SQUAD RATINGS (avg {avg_rat:.1f}/100)",
            f"  {'Player':<20} Ovr   Bat   Bowl  Form  G",
            "  " + "─" * 48,
        ]
        for r in sorted_r:
            name = r.get("player_name", "Unknown")
            if len(name) > 20:
                name = name[:17] + "..."
            lines.append(
                f"  {name:<20} {r.get('overall_rating', 0):4.1f}  "
                f"{r.get('batting_rating', 0):4.1f}  {r.get('bowling_rating', 0):4.1f}  "
                f"{r.get('form_score', 0):4.1f}  {r.get('games_played', 0)}"
            )

        lines += [
            "",
            "KEY PLAYERS",
            f"  Overall: {', '.join(r.get('player_name', '?') for r in sorted_r[:3])}",
            f"  Batting: {', '.join(r.get('player_name', '?') for r in top_bat)}",
            f"  Bowling: {', '.join(r.get('player_name', '?') for r in top_bwl)}",
        ]

    return "\n".join(lines)


def format_live_scorecard(scorecard: dict) -> str:
    """Format a live match scorecard."""
    if not scorecard:
        return "❌ Scorecard unavailable."

    team_a = scorecard.get("team_a", scorecard.get("team1", "Team A"))
    team_b = scorecard.get("team_b", scorecard.get("team2", "Team B"))
    status = scorecard.get("status", "Live")

    lines = [
        f"🔴 LIVE — {team_a} vs {team_b}",
        f"Status: {status}",
        "",
    ]

    for i, inn in enumerate(scorecard.get("innings", []), 1):
        team = inn.get("batting_team", f"Innings {i}")
        runs = inn.get("total_runs", 0)
        wkts = inn.get("total_wickets", 0)
        overs = inn.get("total_overs", 0)
        lines.append(f"  {team}: {runs}/{wkts} ({overs} ov)")

        # Current batsmen
        batsmen = inn.get("current_batsmen", [])
        for b in batsmen:
            name = b.get("name", "")
            if name:
                lines.append(f"    🏏 {name}: {b.get('runs', 0)} ({b.get('balls', 0)}b)")

        # Current bowler
        bowler = inn.get("current_bowler", {})
        if bowler.get("name"):
            lines.append(
                f"    ⚾ {bowler['name']}: {bowler.get('wickets', 0)}/{bowler.get('runs', 0)} "
                f"({bowler.get('overs', 0)} ov)"
            )

    if scorecard.get("score_summary"):
        lines += ["", scorecard["score_summary"]]

    return "\n".join(lines)


def format_elo_rankings(rankings: list, fmt: str) -> str:
    """Format Elo team rankings."""
    if not rankings:
        return f"No Elo data found for {fmt}."

    lines = [
        f"🏅 GLOBAL ELO RANKINGS — {fmt}",
        "",
        f"  {'#':<3} {'Team':<28} Elo",
        "  " + "─" * 42,
    ]

    for i, r in enumerate(rankings, 1):
        team = r.get("team", r.get("team_name", "Unknown"))
        elo = r.get("elo", 1500)
        bar_len = max(0, int((elo - 1300) / 800 * 12))
        lines.append(f"  {i:<3} {team:<28} {elo:.1f}  {'█' * bar_len}")

    return "\n".join(lines)


def format_top_players(players: list, fmt: str) -> str:
    """Format top players leaderboard."""
    if not players:
        return f"No player data found for {fmt}."

    lines = [
        f"⭐ TOP 20 {fmt} PLAYERS",
        "",
        f"  {'#':<3} {'Player':<22} Ovr   Bat   Bowl  Form  G",
        "  " + "─" * 55,
    ]

    for i, p in enumerate(players, 1):
        name = p.get("player_name", "Unknown")
        if len(name) > 22:
            name = name[:19] + "..."
        lines.append(
            f"  {i:<3} {name:<22} {p.get('overall_rating', 0):4.1f}  "
            f"{p.get('batting_rating', 0):4.1f}  {p.get('bowling_rating', 0):4.1f}  "
            f"{p.get('form_score', 0):4.1f}  {p.get('games_played', 0)}"
        )

    return "\n".join(lines)
