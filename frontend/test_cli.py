"""
test_cli.py
CricketIQ — Interactive CLI

Usage: python frontend/test_cli.py
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv()


# ─── UI Primitives ─────────────────────────────────────────

W = 60  # display width

def header(title: str):
    print(f"\n  {'═'*W}")
    print(f"  {title}")
    print(f"  {'═'*W}")

def section(title: str):
    print(f"\n  {title}")
    print(f"  {'─'*W}")

def separator():
    print(f"  {'─'*W}")

def rating_bar(score: float, width: int = 24) -> str:
    filled = int(score / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score:.1f}/100"


# ─── Navigation Helpers ────────────────────────────────────

def select_match_type() -> str:
    """Numbered match type menu."""
    types = ["T20", "ODI", "Test"]
    print("\n  Format:")
    for i, t in enumerate(types, 1):
        print(f"    {i}. {t}")
    choice = input("\n  Select (1-3) [default: 1 = T20]: ").strip() or "1"
    try:
        return types[int(choice) - 1]
    except (ValueError, IndexError):
        return "T20"


def _competition_filter(match_type: str) -> str:
    if match_type == "T20":
        return "AND competition = 'T20I'"
    elif match_type == "ODI":
        return "AND competition = 'ODI'"
    return ""


def get_all_teams(match_type: str) -> list:
    """All teams with data in DB for a given format (no IPL)."""
    from database.db import get_connection
    cf = _competition_filter(match_type)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT DISTINCT team1 AS team FROM matches
        WHERE match_type = ? AND gender = 'male' {cf}
        UNION
        SELECT DISTINCT team2 AS team FROM matches
        WHERE match_type = ? AND gender = 'male' {cf}
        ORDER BY team
    """, (match_type, match_type)).fetchall()
    conn.close()
    return [r["team"] for r in rows]


def select_team(match_type: str, prompt: str = "Select team") -> str:
    """Numbered team list with name search fallback."""
    teams = get_all_teams(match_type)
    if not teams:
        return input(f"  {prompt}: ").strip()

    print(f"\n  {prompt} ({match_type}):")
    cols = 3
    for i in range(0, len(teams), cols):
        row = teams[i:i+cols]
        line = "".join(f"  {i+j+1:3}. {t:<22}" for j, t in enumerate(row))
        print(line)

    while True:
        raw = input("\n  Enter number or team name: ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(teams):
                return teams[idx]
        except ValueError:
            matches = [t for t in teams if raw.lower() in t.lower()]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                print(f"  Multiple matches: {', '.join(matches[:6])}")
                continue
            return raw
        print(f"  Invalid. Enter 1-{len(teams)} or a team name.")


def get_team_player_list(team: str, match_type: str) -> list:
    """Players for a team, ordered by most games first."""
    from database.db import get_connection
    cf = _competition_filter(match_type)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT pms.player_name, COUNT(DISTINCT m.id) AS games
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.team = ? AND m.match_type = ? AND m.gender = 'male' {cf}
        GROUP BY pms.player_name
        ORDER BY games DESC, pms.player_name
    """, (team, match_type)).fetchall()
    conn.close()
    return [r["player_name"] for r in rows]


def select_player(team: str, match_type: str) -> str:
    """Paged player list with number/name selection."""
    players = get_team_player_list(team, match_type)
    if not players:
        return input("  Player name: ").strip()

    PAGE = 24
    page = 0

    while True:
        start = page * PAGE
        end = min(start + PAGE, len(players))
        print(f"\n  Players — {team} ({match_type})  [{len(players)} total, showing {start+1}-{end}]")
        separator()
        cols = 2
        chunk = players[start:end]
        for i in range(0, len(chunk), cols):
            row = chunk[i:i+cols]
            line = "".join(f"  {start+i+j+1:3}. {p:<28}" for j, p in enumerate(row))
            print(line)
        separator()

        nav_hint = ""
        if end < len(players):
            nav_hint += "  'n' next page"
        if page > 0:
            nav_hint += "  'p' prev page"
        if nav_hint:
            print(nav_hint)

        raw = input("\n  Enter number, name, or search: ").strip()

        if raw.lower() == "n" and end < len(players):
            page += 1
            continue
        if raw.lower() == "p" and page > 0:
            page -= 1
            continue

        try:
            idx = int(raw) - 1
            if 0 <= idx < len(players):
                return players[idx]
        except ValueError:
            hits = [p for p in players if raw.lower() in p.lower()]
            if len(hits) == 1:
                return hits[0]
            if hits:
                print(f"\n  Matches:")
                for i, h in enumerate(hits[:10], 1):
                    print(f"    {i}. {h}")
                sub = input("  Select: ").strip()
                try:
                    return hits[int(sub) - 1]
                except Exception:
                    return raw
        print(f"  Not found. Enter a number (1-{len(players)}) or a name.")


def get_recent_innings(player_name: str, match_type: str, n: int = 10) -> list:
    """Last N batting innings with match context."""
    from database.db import get_connection
    cf = _competition_filter(match_type)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT pms.runs, pms.balls_faced, pms.dismissed, pms.fours, pms.sixes,
               m.date, m.team1, m.team2, pms.team
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.player_name = ?
          AND m.match_type = ?
          AND m.gender = 'male'
          {cf}
          AND pms.balls_faced > 0
        ORDER BY m.date DESC
        LIMIT ?
    """, (player_name, match_type, n)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_bowling(player_name: str, match_type: str, n: int = 10) -> list:
    """Last N bowling appearances with match context."""
    from database.db import get_connection
    cf = _competition_filter(match_type)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT pms.overs_bowled, pms.runs_conceded, pms.wickets, pms.dot_balls,
               m.date, m.team1, m.team2, pms.team
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.player_name = ?
          AND m.match_type = ?
          AND m.gender = 'male'
          {cf}
          AND pms.overs_bowled > 0
        ORDER BY m.date DESC
        LIMIT ?
    """, (player_name, match_type, n)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Feature 1: Match Prediction ──────────────────────────

def run_match_prediction():
    header("MATCH PREDICTION ENGINE")
    match_type = select_match_type()
    team1 = select_team(match_type, "Select Team 1")
    team2 = select_team(match_type, "Select Team 2")

    venue = input("\n  Venue (Enter to skip): ").strip() or None
    toss_input = input(f"  Toss winner? (1={team1} / 2={team2} / Enter to skip): ").strip()
    toss = team1 if toss_input == "1" else (team2 if toss_input == "2" else None)

    print(f"\n  Running prediction: {team1} vs {team2} ({match_type})...")
    separator()

    results = {}

    try:
        from models.elo import win_probability, get_elo
        elo_prob = win_probability(team1, team2, match_type)
        elo1 = get_elo(team1, match_type)
        elo2 = get_elo(team2, match_type)
        results["elo_prob"] = elo_prob * 100
        print(f"  [Elo]         {team1}: {elo_prob*100:.1f}%   (Elo: {elo1:.0f} vs {elo2:.0f})")
    except Exception as e:
        print(f"  [Elo] Error: {e}")
        results["elo_prob"] = 50.0

    try:
        from features.team_features import get_team_strength
        s1 = get_team_strength(team1, match_type, venue)
        s2 = get_team_strength(team2, match_type, venue)
        sp = s1 / (s1 + s2) * 100 if (s1 + s2) > 0 else 50
        results["strength_prob"] = sp
        results["strength_diff"] = s1 - s2
        print(f"  [Strength]    {team1}: {sp:.1f}%   (Score: {s1:.1f} vs {s2:.1f})")
    except Exception as e:
        print(f"  [Strength] Error: {e}")
        results["strength_prob"] = 50.0

    try:
        from models.logistic import predict as lr_predict
        lr_prob = lr_predict(team1, team2, venue, match_type, toss) * 100
        results["lr_prob"] = lr_prob
        print(f"  [Logistic]    {team1}: {lr_prob:.1f}%")
    except Exception:
        print(f"  [Logistic]    Not available")
        results["lr_prob"] = results.get("elo_prob", 50.0)

    try:
        from models.xgboost_model import predict as xgb_predict
        xgb_prob = xgb_predict(team1, team2, venue, match_type, toss) * 100
        results["xgb_prob"] = xgb_prob
        print(f"  [XGBoost]     {team1}: {xgb_prob:.1f}%")
    except Exception:
        print(f"  [XGBoost]     Not available")
        results["xgb_prob"] = results.get("elo_prob", 50.0)

    try:
        from simulation.monte_carlo import simulate_match
        print(f"  [Monte Carlo] Running 2000 simulations...", end="", flush=True)
        mc = simulate_match(team1, team2, match_type, n_simulations=2000)
        results["mc_prob"] = mc["team1_win_pct"]
        print(f" Done.  {team1}: {mc['team1_win_pct']:.1f}%")
    except Exception as e:
        print(f"\n  [Monte Carlo] Error: {e}")
        results["mc_prob"] = results.get("elo_prob", 50.0)

    probs = [results.get(k, 50) for k in ["elo_prob", "lr_prob", "xgb_prob", "mc_prob"]]
    final = sum(probs) / len(probs)
    margin = abs(final - 50)
    confidence = "HIGH" if margin >= 15 else ("MEDIUM" if margin >= 7 else "LOW")
    conf_stars = "★★★" if margin >= 15 else ("★★☆" if margin >= 7 else "★☆☆")

    section("PREDICTION RESULT")
    print(f"  {team1:<28}  {final:.1f}%")
    print(f"  {team2:<28}  {100-final:.1f}%")
    print(f"\n  Confidence: {confidence} {conf_stars}")

    # Layer breakdown
    print(f"\n  {'Model':<16} {team1}")
    print(f"  {'─'*36}")
    print(f"  {'Elo':<16} {results.get('elo_prob', 50):.1f}%")
    print(f"  {'Logistic':<16} {results.get('lr_prob', 50):.1f}%")
    print(f"  {'XGBoost':<16} {results.get('xgb_prob', 50):.1f}%")
    print(f"  {'Monte Carlo':<16} {results.get('mc_prob', 50):.1f}%")
    print(f"  {'─'*36}")
    print(f"  {'ENSEMBLE':<16} {final:.1f}%")

    # Head-to-head
    try:
        from features.team_features import get_head_to_head
        h2h = get_head_to_head(team1, team2, match_type)
        if h2h["total"] > 0:
            section(f"HEAD-TO-HEAD  ({h2h['total']} matches)")
            print(f"  {team1}: {h2h['team1_wins']} wins  ({h2h['team1_win_pct']:.0f}%)")
            print(f"  {team2}: {h2h['team2_wins']} wins")
    except Exception:
        pass

    # LLM / rule-based analysis
    try:
        from nlp.report_generator import generate_match_explanation
        explanation = generate_match_explanation(team1, team2, results)
        if explanation:
            section("KEY FACTORS")
            for line in explanation.split("\n"):
                if line.strip():
                    print(f"  {line}")
    except Exception:
        pass


# ─── Feature 2: Player Rating ──────────────────────────────

def run_player_rating():
    header("PLAYER PROFILE")
    match_type = select_match_type()
    team = select_team(match_type, "Select team")
    player = select_player(team, match_type)

    from ratings.player_ratings import get_player_rating
    from features.player_features import (get_batting_stats, get_bowling_stats,
                                           get_player_role)
    from tabulate import tabulate

    rating   = get_player_rating(player, match_type)
    batting  = get_batting_stats(player, match_type)
    bowling  = get_bowling_stats(player, match_type)
    role     = get_player_role(player, match_type)
    r_bat    = get_recent_innings(player, match_type, n=10)
    r_bowl   = get_recent_bowling(player, match_type, n=10)

    # ── Header ──────────────────────────────────────────────
    header(f"{player.upper()}  |  {match_type}  |  {role.title()}")

    # ── Ratings ─────────────────────────────────────────────
    section("RATINGS")
    print(f"  Overall     {rating_bar(rating['overall_rating'])}")
    print(f"  Batting     {rating_bar(rating['batting_rating'])}")
    print(f"  Bowling     {rating_bar(rating['bowling_rating'])}")
    print(f"  Form        {rating_bar(rating['form_score'])}")
    print(f"  Consistency {rating_bar(rating['consistency'])}")
    print(f"\n  Games played: {rating['games_played']}")

    # ── Career Batting ───────────────────────────────────────
    if batting["innings"] > 0:
        section("CAREER BATTING")
        print(f"  {'Innings:':<16} {batting['innings']:>6}   │  {'Total Runs:':<16} {batting['total_runs']:>7,}")
        print(f"  {'Average:':<16} {batting['average']:>6.2f}   │  {'Strike Rate:':<16} {batting['strike_rate']:>7.2f}")
        print(f"  {'Highest:':<16} {batting['highest']:>6}   │  {'Dismissals:':<16} {batting['dismissals']:>7}")
        print(f"  {'50s:':<16} {batting['fifties']:>6}   │  {'100s:':<16} {batting['hundreds']:>7}")
        print(f"  {'Std Dev:':<16} {batting['std_dev']:>6.1f}   │  {'(lower = consistent)'}")

    # ── Recent Batting ───────────────────────────────────────
    if r_bat:
        section(f"RECENT FORM — Last {len(r_bat)} Innings")
        table = []
        for r in r_bat:
            opp = r["team2"] if r["team"] == r["team1"] else r["team1"]
            sr = round(r["runs"] / r["balls_faced"] * 100, 1) if r["balls_faced"] > 0 else 0
            not_out = "" if r["dismissed"] else "*"
            table.append([
                r["date"],
                f"{r['runs']}{not_out}",
                r["balls_faced"],
                f"{sr:.1f}",
                f"{r['fours']}x4  {r['sixes']}x6",
                f"vs {opp}",
            ])
        print(tabulate(table,
                       headers=["Date", "Score", "Balls", "SR", "Boundaries", "Opposition"],
                       tablefmt="simple"))

        # Mini form summary
        recent_runs  = sum(r["runs"] for r in r_bat)
        recent_inns  = len(r_bat)
        recent_disms = sum(r["dismissed"] for r in r_bat)
        recent_avg   = round(recent_runs / recent_disms, 2) if recent_disms > 0 else recent_runs
        recent_balls = sum(r["balls_faced"] for r in r_bat)
        recent_sr    = round(recent_runs / recent_balls * 100, 2) if recent_balls > 0 else 0
        print(f"\n  Last {recent_inns} innings avg: {recent_avg}  |  SR: {recent_sr}  |  Runs: {recent_runs}")

    # ── Career Bowling ───────────────────────────────────────
    if bowling["total_wickets"] > 0:
        section("CAREER BOWLING")
        print(f"  {'Wickets:':<16} {bowling['total_wickets']:>6}   │  {'Overs:':<16} {bowling['total_overs']:>7.1f}")
        print(f"  {'Economy:':<16} {bowling['economy']:>6.2f}   │  {'Bowling Avg:':<16} {bowling['bowling_average']:>7.2f}")
        print(f"  {'Strike Rate:':<16} {bowling['bowling_strike_rate']:>6.1f}   │  {'Dot Ball %:':<16} {bowling['dot_pct']:>7.1f}%")
        if bowling["five_wickets"] > 0:
            print(f"  5-wicket hauls: {bowling['five_wickets']}")

        if r_bowl:
            section(f"RECENT BOWLING — Last {len(r_bowl)} Appearances")
            btable = []
            for r in r_bowl:
                opp  = r["team2"] if r["team"] == r["team1"] else r["team1"]
                econ = round(r["runs_conceded"] / r["overs_bowled"], 2) if r["overs_bowled"] > 0 else 0
                btable.append([
                    r["date"],
                    f"{r['overs_bowled']:.1f}",
                    r["runs_conceded"],
                    r["wickets"],
                    f"{econ:.2f}",
                    r["dot_balls"],
                    f"vs {opp}",
                ])
            print(tabulate(btable,
                           headers=["Date", "Overs", "Runs", "Wkts", "Econ", "Dots", "Opposition"],
                           tablefmt="simple"))


# ─── Feature 3: PVOR Impact ────────────────────────────────

def run_pvor():
    header("PVOR — PLAYER IMPACT ENGINE")
    match_type = select_match_type()
    print("\n  Player's team:")
    team = select_team(match_type, "Select team")
    player = select_player(team, match_type)
    print("\n  Opponent team:")
    opponent = select_team(match_type, "Select opponent")

    print(f"\n  Computing PVOR for {player}...")
    print(f"  (Runs ~2000 simulations with and without player — takes ~10s)")

    from impact.pvor import compute_pvor
    result = compute_pvor(player, team, opponent, match_type)

    section(f"PVOR RESULT — {result['player']}")
    print(f"  Win probability WITH    {result['player']:<25}  {result['win_with']:.1f}%")
    print(f"  Win probability WITHOUT {result['player']:<25}  {result['win_without']:.1f}%")
    print(f"\n  PVOR Impact:   {result['pvor']:+.2f}%")
    print(f"  Impact Label:  {result['impact_label']}")

    labels = {"Elite": "★★★★★", "High": "★★★★☆",
              "Medium": "★★★☆☆", "Low": "★★☆☆☆", "Negative": "★☆☆☆☆"}
    print(f"  Stars:         {labels.get(result['impact_label'], '─')}")


# ─── Feature 4: Player Report ──────────────────────────────

def run_player_report():
    header("PLAYER ANALYSIS REPORT")
    match_type = select_match_type()
    team = select_team(match_type, "Select team")
    player = select_player(team, match_type)

    from ratings.player_ratings import get_player_rating
    from features.player_features import (get_batting_stats, get_bowling_stats,
                                           get_player_role, get_recent_form)
    from tabulate import tabulate

    rating   = get_player_rating(player, match_type)
    batting  = get_batting_stats(player, match_type)
    bowling  = get_bowling_stats(player, match_type)
    role     = get_player_role(player, match_type)
    form_now = get_recent_form(player, match_type, n=10)
    form_old = get_recent_form(player, match_type, n=20)
    r_bat    = get_recent_innings(player, match_type, n=5)
    r_bowl   = get_recent_bowling(player, match_type, n=5)

    header(f"REPORT: {player.upper()}  ({match_type})")
    print(f"  Role: {role.title()}  |  Games: {rating['games_played']}")

    # ── Summary ratings ──────────────────────────────────────
    section("RATING SUMMARY")
    print(f"  Overall     {rating_bar(rating['overall_rating'])}")
    print(f"  Batting     {rating_bar(rating['batting_rating'])}")
    print(f"  Bowling     {rating_bar(rating['bowling_rating'])}")
    print(f"  Form        {rating_bar(form_now)}")

    trend = form_now - form_old
    trend_str = f"▲ +{trend:.1f}" if trend > 2 else (f"▼ {trend:.1f}" if trend < -2 else "→ Stable")
    print(f"\n  Form Trend: {trend_str}  (recent vs older form)")

    # ── Batting profile ──────────────────────────────────────
    if batting["innings"] > 0:
        section("BATTING PROFILE")
        print(f"  Innings: {batting['innings']}  |  Runs: {batting['total_runs']:,}  |  "
              f"Avg: {batting['average']}  |  SR: {batting['strike_rate']}")
        print(f"  Highest: {batting['highest']}  |  50s: {batting['fifties']}  |  "
              f"100s: {batting['hundreds']}  |  Consistency σ: {batting['std_dev']}")

        # Benchmarks
        avg_grade = ("Elite" if batting["average"] >= 45 else
                     "Good" if batting["average"] >= 35 else
                     "Average" if batting["average"] >= 25 else "Below Average")
        sr_grade  = ("Explosive" if batting["strike_rate"] >= 150 else
                     "Good" if batting["strike_rate"] >= 125 else
                     "Moderate" if batting["strike_rate"] >= 100 else "Slow")
        print(f"\n  Average Grade:      {avg_grade}")
        print(f"  Strike Rate Grade:  {sr_grade}")

        if r_bat:
            last5_runs = sum(r["runs"] for r in r_bat)
            print(f"  Last 5 innings:     {[r['runs'] for r in r_bat]}  (total {last5_runs})")

    # ── Bowling profile ──────────────────────────────────────
    if bowling["total_wickets"] > 0:
        section("BOWLING PROFILE")
        print(f"  Wickets: {bowling['total_wickets']}  |  Overs: {bowling['total_overs']}  |  "
              f"Economy: {bowling['economy']}  |  Avg: {bowling['bowling_average']}")
        print(f"  Strike Rate: {bowling['bowling_strike_rate']}  |  Dot %: {bowling['dot_pct']}%  |  "
              f"5-fers: {bowling['five_wickets']}")

        econ_grade = ("Elite" if bowling["economy"] <= 6.0 else
                      "Good" if bowling["economy"] <= 7.5 else
                      "Average" if bowling["economy"] <= 9.0 else "Expensive")
        print(f"\n  Economy Grade: {econ_grade}")

        if r_bowl:
            last5_wkts = sum(r["wickets"] for r in r_bowl)
            print(f"  Last 5 outings: {[r['wickets'] for r in r_bowl]} wickets  (total {last5_wkts})")

    # ── Strengths & Weaknesses ───────────────────────────────
    section("STRENGTHS & WEAKNESSES")

    strengths, weaknesses = [], []

    if batting["innings"] > 0:
        if batting["average"] >= 35:
            strengths.append("Consistent run-scorer — high career average")
        elif batting["average"] < 20:
            weaknesses.append("Below-average batting consistency")
        if batting["strike_rate"] >= 140:
            strengths.append("Explosive strike rate — impact batter")
        elif batting["strike_rate"] < 110:
            weaknesses.append("Slow strike rate — T20 liability")
        if batting["std_dev"] < 20:
            strengths.append("Predictable performer — high consistency")
        elif batting["std_dev"] > 40:
            weaknesses.append("Boom or bust — very inconsistent")
        if batting["hundreds"] >= 3:
            strengths.append(f"{batting['hundreds']} centuries — proven big-match performer")

    if bowling["total_wickets"] > 0:
        if bowling["economy"] <= 7.0:
            strengths.append("Economical bowler — controls run rate well")
        elif bowling["economy"] >= 9.0:
            weaknesses.append("Expensive bowler — high economy rate")
        if bowling["bowling_average"] <= 25:
            strengths.append("Sharp wicket-taker — strong match impact")
        if bowling["bowling_strike_rate"] <= 15:
            strengths.append("Takes wickets quickly — low strike rate")
        if bowling["dot_pct"] >= 35:
            strengths.append(f"High dot ball % ({bowling['dot_pct']}%) — builds pressure")

    if not strengths:
        strengths.append("Insufficient data — needs more games")

    print("  Strengths:")
    for s in strengths:
        print(f"    + {s}")
    if weaknesses:
        print("  Weaknesses:")
        for w in weaknesses:
            print(f"    - {w}")

    # ── LLM enhancement if available ────────────────────────
    try:
        from nlp.report_generator import generate_player_report
        llm_text = generate_player_report(player, match_type)
        if llm_text and "Player Report:" not in llm_text:
            section("AI ANALYSIS")
            for line in llm_text.split("\n"):
                if line.strip():
                    print(f"  {line}")
    except Exception:
        pass


# ─── Feature 5: Team Analysis ──────────────────────────────

def run_team_analysis():
    header("TEAM ANALYSIS")
    match_type = select_match_type()
    team = select_team(match_type, "Select team")

    from features.team_features import get_team_recent_form, get_team_squad
    from ratings.player_ratings import get_player_rating
    from models.elo import get_elo
    from tabulate import tabulate

    print(f"\n  Analysing {team} ({match_type})...")

    elo   = get_elo(team, match_type)
    form  = get_team_recent_form(team, match_type, n=10)
    form5 = get_team_recent_form(team, match_type, n=5)
    squad = get_team_squad(team, match_type, last_n_matches=5)[:15]

    section(f"TEAM OVERVIEW — {team}")
    print(f"  Elo Rating:       {elo:.1f}")
    print(f"  Form (last 10):   {form:.1f}%  {'▲ Hot' if form >= 70 else ('▼ Cold' if form <= 30 else '→ Neutral')}")
    print(f"  Form (last 5):    {form5:.1f}%")

    if squad:
        ratings = [get_player_rating(p, match_type) for p in squad]
        avg_rat = sum(r["overall_rating"] for r in ratings) / len(ratings)
        top3    = sorted(ratings, key=lambda x: x["overall_rating"], reverse=True)[:3]
        top_bat = sorted(ratings, key=lambda x: x["batting_rating"], reverse=True)[:3]
        top_bwl = sorted(ratings, key=lambda x: x["bowling_rating"], reverse=True)[:3]

        section("SQUAD RATINGS")
        print(f"  Average squad rating: {avg_rat:.1f}/100\n")
        table = [[r["player_name"],
                  f"{r['overall_rating']:.1f}",
                  f"{r['batting_rating']:.1f}",
                  f"{r['bowling_rating']:.1f}",
                  f"{r['form_score']:.1f}",
                  r["games_played"]]
                 for r in sorted(ratings, key=lambda x: x["overall_rating"], reverse=True)]
        print(tabulate(table,
                       headers=["Player", "Overall", "Batting", "Bowling", "Form", "Games"],
                       tablefmt="simple"))

        section("KEY PLAYERS")
        print(f"  Top overall:  {', '.join(r['player_name'] for r in top3)}")
        print(f"  Top batters:  {', '.join(r['player_name'] for r in top_bat)}")
        print(f"  Top bowlers:  {', '.join(r['player_name'] for r in top_bwl)}")

    # LLM or rule-based analysis
    try:
        from nlp.report_generator import generate_team_analysis
        analysis = generate_team_analysis(team, match_type)
        if analysis:
            section("ANALYSIS")
            print(analysis)
    except Exception:
        pass


# ─── Feature 6: Top Players ────────────────────────────────

def run_top_players():
    header("TOP PLAYERS LEADERBOARD")
    match_type = select_match_type()

    print("\n  Role filter:")
    print("    1. Overall")
    print("    2. Batting only")
    print("    3. Bowling only")
    role_choice = input("\n  Select (1-3) [default: 1]: ").strip() or "1"
    role_map = {"1": "overall", "2": "batting", "3": "bowling"}
    role = role_map.get(role_choice, "overall")

    # Optional team filter
    team_filter = input("\n  Filter by team? (Enter team name or press Enter for all): ").strip()

    n = int(input("  How many to show? [default 20]: ").strip() or "20")

    from ratings.player_ratings import get_top_players
    from database.db import get_connection
    from tabulate import tabulate

    players = get_top_players(match_type, n=n * 3, role=role)  # fetch extra in case team filter

    if team_filter:
        # Filter by team membership
        cf = _competition_filter(match_type)
        conn = get_connection()
        team_players = set(
            r["player_name"] for r in conn.execute(f"""
                SELECT DISTINCT pms.player_name
                FROM player_match_stats pms
                JOIN matches m ON pms.match_id = m.id
                WHERE pms.team = ? AND m.match_type = ? AND m.gender = 'male' {cf}
            """, (team_filter, match_type)).fetchall()
        )
        conn.close()
        players = [p for p in players if p["player_name"] in team_players]

    players = players[:n]

    if not players:
        print("  No data found.")
        return

    section(f"TOP {len(players)} {match_type} {role.upper()} PLAYERS"
            + (f" — {team_filter}" if team_filter else ""))
    table = [[i,
              p["player_name"],
              f"{p['overall_rating']:.1f}",
              f"{p['batting_rating']:.1f}",
              f"{p['bowling_rating']:.1f}",
              f"{p['form_score']:.1f}",
              p["games_played"]]
             for i, p in enumerate(players, 1)]
    print(tabulate(table,
                   headers=["#", "Player", "Overall", "Batting", "Bowling", "Form", "Games"],
                   tablefmt="simple"))


# ─── Feature 7: Smart Alerts ──────────────────────────────

def run_smart_alerts():
    header("SMART MATCH ALERTS")
    match_type = select_match_type()
    team1 = select_team(match_type, "Select Team 1")
    team2 = select_team(match_type, "Select Team 2")

    from models.elo import win_probability
    from features.team_features import get_team_recent_form, get_head_to_head

    elo_prob = win_probability(team1, team2, match_type) * 100
    form1  = get_team_recent_form(team1, match_type)
    form2  = get_team_recent_form(team2, match_type)
    h2h    = get_head_to_head(team1, team2, match_type)
    margin = abs(elo_prob - 50)

    section(f"ALERTS — {team1} vs {team2}  ({match_type})")
    print(f"  Elo win probability: {team1} {elo_prob:.1f}% | {team2} {100-elo_prob:.1f}%")
    print(f"  Recent form:         {team1} {form1:.0f}%  |  {team2} {form2:.0f}%")
    if h2h["total"] > 0:
        print(f"  Head-to-head:        {team1} {h2h['team1_wins']}-{h2h['team2_wins']} {team2}  ({h2h['total']} matches)")

    section("SIGNALS")
    alerts = []

    if margin >= 20:
        winner = team1 if elo_prob >= 50 else team2
        alerts.append(f"HIGH CONFIDENCE: {winner} heavily favored — {max(elo_prob, 100-elo_prob):.0f}% win prob")

    if margin >= 10:
        winner = team1 if elo_prob >= 50 else team2
        alerts.append(f"MODERATE EDGE: {winner} has a clear Elo advantage")

    if abs(form1 - form2) >= 30:
        in_form = team1 if form1 > form2 else team2
        alerts.append(f"FORM ALERT: {in_form} on a strong run — {max(form1, form2):.0f}% win rate last 10")

    if h2h["total"] >= 10 and h2h["team1_win_pct"] >= 65:
        alerts.append(f"H2H DOMINANCE: {team1} wins {h2h['team1_win_pct']:.0f}% of head-to-heads")
    elif h2h["total"] >= 10 and h2h["team1_win_pct"] <= 35:
        alerts.append(f"H2H DOMINANCE: {team2} dominates this fixture historically")

    if form1 >= 70 and form2 >= 70:
        alerts.append("BOTH IN FORM: High-quality matchup expected — close contest likely")

    if margin < 5:
        alerts.append("COIN FLIP: Extremely close — high uncertainty, any result possible")

    if not alerts:
        alerts.append("No strong signals. Match is competitive with no clear edge.")

    for alert in alerts:
        print(f"  ⚡ {alert}")


# ─── Feature 8: Elo Rankings ───────────────────────────────

def run_elo_rankings():
    header("GLOBAL ELO RANKINGS")
    match_type = select_match_type()

    from models.elo import get_top_elo_rankings
    from tabulate import tabulate

    rankings = get_top_elo_rankings(match_type, n=25)

    if not rankings:
        print("  No Elo data. Run: python backend/models/elo.py")
        return

    section(f"TOP {len(rankings)} TEAMS — {match_type} ELO")
    table = [[i, r["team"], f"{r['elo']:.1f}",
              "█" * int(r["elo"] / 100)]
             for i, r in enumerate(rankings, 1)]
    print(tabulate(table, headers=["#", "Team", "Elo", ""], tablefmt="simple"))


# ─── Main Menu ─────────────────────────────────────────────

def main():
    print("\n")
    print("  ██████╗██████╗ ██╗ ██████╗██╗  ██╗███████╗████████╗██╗ ██████╗ ")
    print("  ██╔════╝██╔══██╗██║██╔════╝██║ ██╔╝██╔════╝╚══██╔══╝██║██╔═══██╗")
    print("  ██║     ██████╔╝██║██║     █████╔╝ █████╗     ██║   ██║██║   ██║")
    print("  ██║     ██╔══██╗██║██║     ██╔═██╗ ██╔══╝     ██║   ██║██║▄▄ ██║")
    print("  ╚██████╗██║  ██║██║╚██████╗██║  ██╗███████╗   ██║   ██║╚██████╔╝")
    print("   ╚═════╝╚═╝  ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚══▀▀═╝ ")
    print("                   Cricket Prediction Engine — MVP v2")

    menu = {
        "1": ("Match Prediction",      run_match_prediction),
        "2": ("Player Profile",        run_player_rating),
        "3": ("Player PVOR Impact",    run_pvor),
        "4": ("Player Analysis Report",run_player_report),
        "5": ("Team Analysis",         run_team_analysis),
        "6": ("Top Players",           run_top_players),
        "7": ("Smart Alerts",          run_smart_alerts),
        "8": ("Elo Rankings",          run_elo_rankings),
        "0": ("Exit",                  None),
    }

    while True:
        print(f"\n\n  {'─'*W}")
        print("  MENU")
        print(f"  {'─'*W}")
        for k, (label, _) in menu.items():
            print(f"    {k}.  {label}")
        print(f"  {'─'*W}")

        choice = input("\n  Choose option: ").strip()

        if choice == "0":
            print("\n  Goodbye.\n")
            break
        elif choice in menu:
            label, fn = menu[choice]
            try:
                fn()
            except KeyboardInterrupt:
                print("\n  Cancelled.")
            except Exception as e:
                print(f"\n  Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("  Invalid option. Enter 0-8.")


if __name__ == "__main__":
    main()
