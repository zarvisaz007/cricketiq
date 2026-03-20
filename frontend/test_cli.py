"""
test_cli.py
CricketIQ — Interactive CLI Tester

Run this to test all prediction features locally.
Usage: python test_cli.py
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv()


def header(title: str):
    print("\n" + "=" * 55)
    print(f"  {title}")
    print("=" * 55)


def separator():
    print("-" * 55)


def get_match_types() -> list:
    return ["T20", "ODI", "Test"]


# ─── Feature 1: Match Prediction ──────────────────────────

def run_match_prediction():
    header("MATCH PREDICTION ENGINE")
    team1 = input("  Team 1: ").strip()
    team2 = input("  Team 2: ").strip()

    print("  Match type (T20/ODI/Test):")
    match_type = input("  > ").strip() or "T20"

    venue = input("  Venue (press Enter to skip): ").strip() or None
    toss = input(f"  Toss winner ({team1}/{team2}, press Enter to skip): ").strip() or None

    print("\n  Running prediction layers...")
    separator()

    results = {}

    # Layer 1: Elo
    try:
        from models.elo import win_probability, get_elo
        elo_prob = win_probability(team1, team2, match_type)
        elo1 = get_elo(team1, match_type)
        elo2 = get_elo(team2, match_type)
        results["elo_prob"] = elo_prob * 100
        print(f"  [Elo]         {team1}: {elo_prob*100:.1f}%  |  Elo: {elo1:.0f} vs {elo2:.0f}")
    except Exception as e:
        print(f"  [Elo] Error: {e}")
        results["elo_prob"] = 50.0

    # Layer 2: Team Strength
    try:
        from features.team_features import get_team_strength
        s1 = get_team_strength(team1, match_type, venue)
        s2 = get_team_strength(team2, match_type, venue)
        strength_prob = s1 / (s1 + s2) * 100 if (s1 + s2) > 0 else 50
        results["strength_prob"] = strength_prob
        results["strength_diff"] = s1 - s2
        print(f"  [Strength]    {team1}: {strength_prob:.1f}%  |  Scores: {s1:.1f} vs {s2:.1f}")
    except Exception as e:
        print(f"  [Strength] Error: {e}")
        results["strength_prob"] = 50.0

    # Layer 3: Logistic Regression
    try:
        from models.logistic import predict as logistic_predict
        lr_prob = logistic_predict(team1, team2, venue, match_type, toss) * 100
        results["lr_prob"] = lr_prob
        print(f"  [Logistic]    {team1}: {lr_prob:.1f}%")
    except Exception as e:
        print(f"  [Logistic] Not available (train models first)")
        results["lr_prob"] = results.get("elo_prob", 50.0)

    # Layer 4: XGBoost
    try:
        from models.xgboost_model import predict as xgb_predict
        xgb_prob = xgb_predict(team1, team2, venue, match_type, toss) * 100
        results["xgb_prob"] = xgb_prob
        print(f"  [XGBoost]     {team1}: {xgb_prob:.1f}%")
    except Exception as e:
        print(f"  [XGBoost] Not available (train models first)")
        results["xgb_prob"] = results.get("elo_prob", 50.0)

    # Layer 5: Monte Carlo
    try:
        from simulation.monte_carlo import simulate_match
        print(f"\n  Running Monte Carlo (2000 simulations)...", end="", flush=True)
        mc = simulate_match(team1, team2, match_type, n_simulations=2000)
        results["mc_prob"] = mc["team1_win_pct"]
        results["confidence"] = mc["confidence"]
        print(f"  Done.")
        print(f"  [Monte Carlo] {team1}: {mc['team1_win_pct']:.1f}%")
    except Exception as e:
        print(f"\n  [Monte Carlo] Error: {e}")
        results["mc_prob"] = results.get("elo_prob", 50.0)
        results["confidence"] = "Medium"

    # ─── Final Ensemble ───────────────────────────────────────
    probs = [results.get(k, 50) for k in ["elo_prob", "lr_prob", "xgb_prob", "mc_prob"]]
    final_prob = sum(probs) / len(probs)
    results["final_prob"] = final_prob

    margin = abs(final_prob - 50)
    confidence = "High" if margin >= 15 else ("Medium" if margin >= 7 else "Low")

    separator()
    print(f"\n  {'─'*50}")
    print(f"  PREDICTION: {team1} vs {team2} ({match_type})")
    print(f"  {'─'*50}")
    print(f"  Win Probability:")
    print(f"    {team1:<25} {final_prob:.1f}%")
    print(f"    {team2:<25} {100-final_prob:.1f}%")
    print(f"  Confidence: {confidence}")

    # Head-to-head
    try:
        from features.team_features import get_head_to_head
        h2h = get_head_to_head(team1, team2, match_type)
        if h2h["total"] > 0:
            print(f"\n  Head-to-Head ({h2h['total']} matches):")
            print(f"    {team1}: {h2h['team1_wins']} wins")
            print(f"    {team2}: {h2h['team2_wins']} wins")
    except Exception:
        pass

    # LLM explanation
    try:
        from nlp.report_generator import generate_match_explanation
        explanation = generate_match_explanation(team1, team2, results)
        if explanation:
            print(f"\n  Key Factors:")
            for line in explanation.split("\n"):
                if line.strip():
                    print(f"    {line}")
    except Exception:
        pass


# ─── Feature 2: Player Rating ──────────────────────────────

def run_player_rating():
    header("PLAYER RATING")
    player = input("  Player name: ").strip()
    match_type = input("  Match type (T20/ODI/Test): ").strip() or "T20"

    from ratings.player_ratings import get_player_rating
    from features.player_features import get_batting_stats, get_bowling_stats

    rating = get_player_rating(player, match_type)
    batting = get_batting_stats(player, match_type)
    bowling = get_bowling_stats(player, match_type)

    separator()
    print(f"\n  {player} — {match_type}")
    separator()
    print(f"  Overall Rating:  {rating['overall_rating']:.1f} / 100")
    print(f"  Batting Rating:  {rating['batting_rating']:.1f} / 100")
    print(f"  Bowling Rating:  {rating['bowling_rating']:.1f} / 100")
    print(f"  Form Score:      {rating['form_score']:.1f} / 100")
    print(f"  Games Played:    {rating['games_played']}")

    if batting["innings"] > 0:
        print(f"\n  Batting Stats:")
        print(f"    Innings: {batting['innings']}  |  Average: {batting['average']}  |  SR: {batting['strike_rate']}")
        print(f"    Highest: {batting['highest']}  |  50s: {batting['fifties']}  |  100s: {batting['hundreds']}")

    if bowling["total_wickets"] > 0:
        print(f"\n  Bowling Stats:")
        print(f"    Wickets: {bowling['total_wickets']}  |  Economy: {bowling['economy']}  |  Avg: {bowling['bowling_average']}")


# ─── Feature 3: PVOR Impact ────────────────────────────────

def run_pvor():
    header("PVOR — PLAYER IMPACT ENGINE")
    player = input("  Player name: ").strip()
    team = input("  Player's team: ").strip()
    opponent = input("  Opponent team: ").strip()
    match_type = input("  Match type (T20/ODI/Test): ").strip() or "T20"

    print(f"\n  Computing PVOR for {player}... (runs simulations, takes ~10s)")

    from impact.pvor import compute_pvor
    result = compute_pvor(player, team, opponent, match_type)

    separator()
    print(f"\n  {player} — Impact Analysis")
    separator()
    print(f"  Win WITH {player}:     {result['win_with']:.1f}%")
    print(f"  Win WITHOUT {player}:  {result['win_without']:.1f}%")
    print(f"  PVOR Impact:          {result['pvor']:+.2f}%")
    print(f"  Impact Label:         {result['impact_label']}")


# ─── Feature 4: Player Report ──────────────────────────────

def run_player_report():
    header("PLAYER REPORT ENGINE")
    player = input("  Player name: ").strip()
    match_type = input("  Match type (T20/ODI/Test): ").strip() or "T20"

    from nlp.report_generator import generate_player_report
    print(f"\n  Generating report for {player}...")
    report = generate_player_report(player, match_type)

    separator()
    print(f"\n{report}")


# ─── Feature 5: Team Analysis ──────────────────────────────

def run_team_analysis():
    header("TEAM ANALYSIS")
    team = input("  Team name: ").strip()
    match_type = input("  Match type (T20/ODI/Test): ").strip() or "T20"

    from nlp.report_generator import generate_team_analysis
    from features.team_features import get_team_recent_form, get_head_to_head
    from models.elo import get_elo

    print(f"\n  Analyzing {team}...")
    analysis = generate_team_analysis(team, match_type)

    separator()
    print(f"\n{analysis}")

    elo = get_elo(team, match_type)
    form = get_team_recent_form(team, match_type)
    print(f"\n  Elo Rating: {elo:.1f}")
    print(f"  Recent Form: {form:.1f}% (last 10 matches)")


# ─── Feature 6: Top Players ────────────────────────────────

def run_top_players():
    header("TOP PLAYERS")
    match_type = input("  Match type (T20/ODI/Test): ").strip() or "T20"
    print("  Role (overall/batting/bowling):")
    role = input("  > ").strip() or "overall"
    n = int(input("  How many players to show (default 15): ").strip() or "15")

    from ratings.player_ratings import get_top_players
    from tabulate import tabulate

    players = get_top_players(match_type, n=n, role=role)

    if not players:
        print("  No data. Run ratings first: python ratings/player_ratings.py")
        return

    separator()
    table = []
    for i, p in enumerate(players, 1):
        table.append([
            i,
            p["player_name"],
            f"{p['overall_rating']:.1f}",
            f"{p['batting_rating']:.1f}",
            f"{p['bowling_rating']:.1f}",
            f"{p['form_score']:.1f}",
            p["games_played"],
        ])

    print(tabulate(table,
                   headers=["#", "Player", "Overall", "Batting", "Bowling", "Form", "Games"],
                   tablefmt="simple"))


# ─── Feature 7: Smart Alerts ──────────────────────────────

def run_smart_alerts():
    header("SMART ALERTS")
    print("  Enter upcoming match to analyze:")
    team1 = input("  Team 1: ").strip()
    team2 = input("  Team 2: ").strip()
    match_type = input("  Match type (T20/ODI/Test): ").strip() or "T20"

    from models.elo import win_probability
    from features.team_features import get_team_recent_form

    elo_prob = win_probability(team1, team2, match_type) * 100
    form1 = get_team_recent_form(team1, match_type)
    form2 = get_team_recent_form(team2, match_type)

    margin = abs(elo_prob - 50)

    separator()
    print(f"\n  Smart Alerts for {team1} vs {team2}")
    separator()

    alerts = []

    if margin >= 20:
        winner = team1 if elo_prob >= 50 else team2
        alerts.append(f"HIGH CONFIDENCE: {winner} is heavily favored ({max(elo_prob, 100-elo_prob):.0f}% win prob)")

    if abs(form1 - form2) >= 30:
        in_form = team1 if form1 > form2 else team2
        alerts.append(f"FORM ALERT: {in_form} on a strong run — {max(form1, form2):.0f}% win rate last 10")

    if margin < 5:
        alerts.append("COIN FLIP ALERT: Extremely close match — high uncertainty")

    if not alerts:
        alerts.append("No strong signals. Match is competitive.")

    for alert in alerts:
        print(f"  ⚡ {alert}")


# ─── Feature 8: Elo Rankings ───────────────────────────────

def run_elo_rankings():
    header("ELO RANKINGS")
    match_type = input("  Match type (T20/ODI/Test): ").strip() or "T20"

    from models.elo import get_top_elo_rankings
    from tabulate import tabulate

    rankings = get_top_elo_rankings(match_type, n=20)

    if not rankings:
        print("  No Elo ratings found. Run: python models/elo.py")
        return

    separator()
    table = [[i, r["team"], r["elo"]] for i, r in enumerate(rankings, 1)]
    print(tabulate(table, headers=["#", "Team", "Elo Rating"], tablefmt="simple"))


# ─── Main Menu ─────────────────────────────────────────────

def main():
    print("\n")
    print("  ██████╗██████╗ ██╗ ██████╗██╗  ██╗███████╗████████╗██╗ ██████╗ ")
    print("  ██╔════╝██╔══██╗██║██╔════╝██║ ██╔╝██╔════╝╚══██╔══╝██║██╔═══██╗")
    print("  ██║     ██████╔╝██║██║     █████╔╝ █████╗     ██║   ██║██║   ██║")
    print("  ██║     ██╔══██╗██║██║     ██╔═██╗ ██╔══╝     ██║   ██║██║▄▄ ██║")
    print("  ╚██████╗██║  ██║██║╚██████╗██║  ██╗███████╗   ██║   ██║╚██████╔╝")
    print("   ╚═════╝╚═╝  ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚══▀▀═╝ ")
    print("                   Cricket Prediction Engine — MVP")

    menu = {
        "1": ("Match Prediction",   run_match_prediction),
        "2": ("Player Rating",      run_player_rating),
        "3": ("Player PVOR Impact", run_pvor),
        "4": ("Player Report",      run_player_report),
        "5": ("Team Analysis",      run_team_analysis),
        "6": ("Top Players",        run_top_players),
        "7": ("Smart Alerts",       run_smart_alerts),
        "8": ("Elo Rankings",       run_elo_rankings),
        "0": ("Exit",               None),
    }

    while True:
        print("\n")
        separator()
        print("  MENU")
        separator()
        for k, (label, _) in menu.items():
            print(f"  {k}. {label}")
        separator()

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
            print("  Invalid option.")


if __name__ == "__main__":
    main()
