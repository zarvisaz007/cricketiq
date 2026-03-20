"""
nlp/report_generator.py
Generates player reports and match explanations using OpenRouter LLM.
Falls back to rule-based generation if no API key is set.
"""
import os
import sys
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def _call_llm(prompt: str) -> str:
    """Call OpenRouter API. Returns empty string if unavailable."""
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_key_here":
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return ""


def generate_player_report(player_name: str, match_type: str) -> str:
    """Generate a player analysis report."""
    from ratings.player_ratings import get_player_rating
    from features.player_features import get_batting_stats, get_bowling_stats

    rating = get_player_rating(player_name, match_type)
    batting = get_batting_stats(player_name, match_type)
    bowling = get_bowling_stats(player_name, match_type)

    # Try LLM first
    prompt = f"""Generate a concise cricket player report for {player_name} in {match_type} cricket.
Stats: batting avg={batting['average']}, SR={batting['strike_rate']}, innings={batting['innings']}
Bowling: wickets={bowling['total_wickets']}, economy={bowling['economy']}, avg={bowling['bowling_average']}
Rating: batting={rating['batting_rating']}/100, bowling={rating['bowling_rating']}/100, form={rating['form_score']}/100

Format:
• [2-3 key strengths]
• [1-2 weaknesses]
• Prediction: [expected performance range]

Be specific, actionable, no fluff."""

    llm_output = _call_llm(prompt)
    if llm_output:
        return llm_output

    # Rule-based fallback
    return _rule_based_player_report(player_name, rating, batting, bowling)


def _rule_based_player_report(player_name: str, rating: dict,
                                batting: dict, bowling: dict) -> str:
    lines = [f"Player Report: {player_name}"]
    lines.append("")

    strengths = []
    weaknesses = []

    if batting["innings"] > 0:
        if batting["average"] >= 35:
            strengths.append("Consistent run-scorer with high average")
        elif batting["average"] < 20:
            weaknesses.append("Below-average batting consistency")

        if batting["strike_rate"] >= 140:
            strengths.append("Explosive strike rate, impacts match tempo")
        elif batting["strike_rate"] < 110:
            weaknesses.append("Slow strike rate, may hurt in T20 context")

        if batting["std_dev"] < 20:
            strengths.append("High consistency — predictable performer")
        elif batting["std_dev"] > 40:
            weaknesses.append("Inconsistent — big scores but frequent failures")

    if bowling["total_wickets"] > 0:
        if bowling["economy"] <= 7.0:
            strengths.append("Economical bowler, controls run rate")
        elif bowling["economy"] >= 9.0:
            weaknesses.append("Expensive bowler, high economy rate")

        if bowling["bowling_average"] <= 25:
            strengths.append("Wicket-taking ability — strong match impact")

    if not strengths:
        strengths.append("Limited data — needs more matches")

    lines.append("Strengths:")
    for s in strengths:
        lines.append(f"  • {s}")

    if weaknesses:
        lines.append("Weaknesses:")
        for w in weaknesses:
            lines.append(f"  • {w}")

    lines.append("")
    lines.append(f"Rating: {rating['overall_rating']:.1f}/100  |  Form: {rating['form_score']:.1f}/100")

    return "\n".join(lines)


def generate_match_explanation(team1: str, team2: str, prediction: dict) -> str:
    """Generate a natural language explanation of a match prediction."""
    prompt = f"""Explain this cricket match prediction briefly:

{team1} vs {team2}
Win probability: {team1} {prediction.get('final_prob', 50):.0f}% | {team2} {100-prediction.get('final_prob', 50):.0f}%
Confidence: {prediction.get('confidence', 'Medium')}

Key numbers:
- Team strength diff: {prediction.get('strength_diff', 0):.1f}
- Elo win prob: {prediction.get('elo_prob', 50):.0f}%
- Monte Carlo: {prediction.get('mc_prob', 50):.0f}%

Give 3 bullet points explaining WHY. Be specific, no fluff."""

    llm_output = _call_llm(prompt)
    if llm_output:
        return llm_output

    # Fallback
    winner = team1 if prediction.get("final_prob", 50) >= 50 else team2
    return (f"• {winner} favored based on superior team strength and recent form\n"
            f"• Elo model and simulation both align on same outcome\n"
            f"• Confidence: {prediction.get('confidence', 'Medium')}")


def generate_team_analysis(team: str, match_type: str) -> str:
    """Generate team strengths/weaknesses analysis."""
    from features.team_features import get_team_recent_form, get_team_squad
    from ratings.player_ratings import get_player_rating

    form = get_team_recent_form(team, match_type)
    squad = get_team_squad(team, match_type)[:11]

    if not squad:
        return f"No data available for {team} in {match_type}."

    ratings = [get_player_rating(p, match_type) for p in squad]
    avg_rating = sum(r["overall_rating"] for r in ratings) / len(ratings)
    top_players = sorted(ratings, key=lambda x: x["overall_rating"], reverse=True)[:3]

    prompt = f"""Generate a concise team analysis for {team} in {match_type} cricket.
Recent form: {form:.1f}% win rate (last 10 matches)
Average squad rating: {avg_rating:.1f}/100
Top performers: {', '.join(r['player_name'] for r in top_players)}

Format:
Strength: [2 bullet points]
Weakness: [2 bullet points]
Win Driver: [1 line]

Be specific and actionable."""

    llm_output = _call_llm(prompt)
    if llm_output:
        return llm_output

    # Fallback
    lines = [f"Team Analysis: {team} ({match_type})", ""]
    lines.append(f"Recent Form: {form:.1f}% (last 10 matches)")
    lines.append(f"Squad Avg Rating: {avg_rating:.1f}/100")
    lines.append(f"Key Players: {', '.join(r['player_name'] for r in top_players)}")
    if form >= 60:
        lines.append("Strength: Strong recent form and cohesive squad")
    else:
        lines.append("Weakness: Poor recent form — needs improvement")
    return "\n".join(lines)
