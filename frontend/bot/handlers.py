"""
frontend/bot/handlers.py
CricketIQ Telegram Bot

Usage:
    python frontend/bot/handlers.py
"""
import sys
import os
import asyncio

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters,
)

# ── Conversation states ───────────────────────────────────────
(
    PREDICT_FMT, PREDICT_T1, PREDICT_T2,
    PLAYER_FMT, PLAYER_TEAM, PLAYER_SEL,
    TEAM_FMT, TEAM_SEL,
    TOP_FMT,
    ALERTS_FMT, ALERTS_T1, ALERTS_T2,
    ELO_FMT,
    PVOR_FMT, PVOR_TEAM, PVOR_PLAYER, PVOR_OPP,
) = range(17)

PAGE = 8  # items per inline keyboard page


# ── DB helpers ────────────────────────────────────────────────

def _cf(match_type: str) -> str:
    if match_type == "T20":
        return "AND competition = 'T20I'"
    if match_type == "ODI":
        return "AND competition = 'ODI'"
    return ""


def _teams(match_type: str) -> list:
    from database.db import get_connection
    cf = _cf(match_type)
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


def _players(team: str, match_type: str, limit: int = 60) -> list:
    from database.db import get_connection
    cf = _cf(match_type)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT pms.player_name, COUNT(DISTINCT m.id) AS g
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.team = ? AND m.match_type = ? AND m.gender = 'male' {cf}
        GROUP BY pms.player_name
        ORDER BY g DESC
        LIMIT ?
    """, (team, match_type, limit)).fetchall()
    conn.close()
    return [r["player_name"] for r in rows]


# ── UI helpers ────────────────────────────────────────────────

def fmt_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("T20", callback_data="T20"),
        InlineKeyboardButton("ODI", callback_data="ODI"),
    ]])


def list_kbd(items: list, page: int, prefix: str) -> InlineKeyboardMarkup:
    """Paginated inline keyboard for teams or players."""
    start = page * PAGE
    end = min(start + PAGE, len(items))
    rows = []
    for item in items[start:end]:
        rows.append([InlineKeyboardButton(item, callback_data=f"{prefix}|{item}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"{prefix}_pg|{page - 1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"{prefix}_pg|{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def _bar(score: float, width: int = 14) -> str:
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled) + f" {score:.0f}"


async def _send_long(chat, text: str, parse_mode=None):
    """Send text split into ≤4000-char chunks."""
    MAX = 4000
    for i in range(0, len(text), MAX):
        await chat.send_message(text[i:i + MAX], parse_mode=parse_mode)


# ── /start + /help ────────────────────────────────────────────

WELCOME = (
    "🏏 *CricketIQ Bot*\n\n"
    "AI-powered cricket prediction engine.\n\n"
    "*Commands:*\n"
    "/predict — Match outcome prediction\n"
    "/player — Player profile & stats\n"
    "/team — Team analysis\n"
    "/top — Top players leaderboard\n"
    "/alerts — Smart match alerts\n"
    "/elo — Global Elo rankings\n"
    "/pvor — Player impact (PVOR)\n"
    "/cancel — Cancel current action\n"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


# ── Cancel (global) ───────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Cancelled.")
    else:
        await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
# FEATURE 1: /predict
# ══════════════════════════════════════════════════════════════

async def predict_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Select format:", reply_markup=fmt_kbd())
    return PREDICT_FMT


async def predict_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fmt = q.data
    context.user_data["fmt"] = fmt
    teams = await asyncio.to_thread(_teams, fmt)
    context.user_data["teams"] = teams
    await q.edit_message_text(
        f"Format: {fmt}\nSelect Team 1 ({len(teams)} teams):",
        reply_markup=list_kbd(teams, 0, "pt1"),
    )
    return PREDICT_T1


async def predict_t1_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select Team 1:",
        reply_markup=list_kbd(context.user_data["teams"], page, "pt1"),
    )
    return PREDICT_T1


async def predict_t1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["t1"] = q.data.split("|")[1]
    teams = context.user_data["teams"]
    await q.edit_message_text(
        f"Team 1: {context.user_data['t1']}\nSelect Team 2:",
        reply_markup=list_kbd(teams, 0, "pt2"),
    )
    return PREDICT_T2


async def predict_t2_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select Team 2:",
        reply_markup=list_kbd(context.user_data["teams"], page, "pt2"),
    )
    return PREDICT_T2


async def predict_t2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    team1 = context.user_data["t1"]
    team2 = q.data.split("|")[1]
    fmt = context.user_data["fmt"]

    await q.edit_message_text(f"⏳ Predicting {team1} vs {team2} ({fmt})...")

    def _run():
        r = {}
        try:
            from models.elo import win_probability, get_elo
            r["elo_prob"] = win_probability(team1, team2, fmt) * 100
            r["elo1"] = get_elo(team1, fmt)
            r["elo2"] = get_elo(team2, fmt)
        except Exception:
            r["elo_prob"] = 50.0
            r["elo1"] = r["elo2"] = 1500

        try:
            from models.logistic import predict as lr
            r["lr_prob"] = lr(team1, team2, None, fmt, None) * 100
        except Exception:
            r["lr_prob"] = r["elo_prob"]

        try:
            from models.xgboost_model import predict as xgb
            r["xgb_prob"] = xgb(team1, team2, None, fmt, None) * 100
        except Exception:
            r["xgb_prob"] = r["elo_prob"]

        try:
            from simulation.monte_carlo import simulate_match
            mc = simulate_match(team1, team2, fmt, n_simulations=2000)
            r["mc_prob"] = mc["team1_win_pct"]
        except Exception:
            r["mc_prob"] = r["elo_prob"]

        try:
            from features.team_features import get_head_to_head
            r["h2h"] = get_head_to_head(team1, team2, fmt)
        except Exception:
            r["h2h"] = {"total": 0}

        return r

    r = await asyncio.to_thread(_run)
    final = sum([r["elo_prob"], r["lr_prob"], r["xgb_prob"], r["mc_prob"]]) / 4
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
        f"  Elo          {r['elo_prob']:.1f}%  ({r['elo1']:.0f} vs {r['elo2']:.0f})",
        f"  Logistic     {r['lr_prob']:.1f}%",
        f"  XGBoost      {r['xgb_prob']:.1f}%",
        f"  Monte Carlo  {r['mc_prob']:.1f}%",
        f"  ─────────────────────",
        f"  Ensemble     {final:.1f}%",
    ]

    h2h = r.get("h2h", {})
    if h2h.get("total", 0) > 0:
        lines += [
            "",
            f"HEAD-TO-HEAD ({h2h['total']} matches)",
            f"  {team1}: {h2h['team1_wins']} wins ({h2h['team1_win_pct']:.0f}%)",
            f"  {team2}: {h2h['team2_wins']} wins",
        ]

    await q.message.reply_text("\n".join(lines))
    context.user_data.clear()
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
# FEATURE 2: /player
# ══════════════════════════════════════════════════════════════

async def player_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Select format:", reply_markup=fmt_kbd())
    return PLAYER_FMT


async def player_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fmt = q.data
    context.user_data["fmt"] = fmt
    teams = await asyncio.to_thread(_teams, fmt)
    context.user_data["teams"] = teams
    await q.edit_message_text(
        f"Format: {fmt}\nSelect team:",
        reply_markup=list_kbd(teams, 0, "plteam"),
    )
    return PLAYER_TEAM


async def player_team_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select team:",
        reply_markup=list_kbd(context.user_data["teams"], page, "plteam"),
    )
    return PLAYER_TEAM


async def player_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    team = q.data.split("|")[1]
    fmt = context.user_data["fmt"]
    context.user_data["team"] = team
    players = await asyncio.to_thread(_players, team, fmt)
    context.user_data["players"] = players
    await q.edit_message_text(
        f"Team: {team}\nSelect player ({len(players)} total):",
        reply_markup=list_kbd(players, 0, "plsel"),
    )
    return PLAYER_SEL


async def player_sel_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select player:",
        reply_markup=list_kbd(context.user_data["players"], page, "plsel"),
    )
    return PLAYER_SEL


async def player_sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    player = q.data.split("|")[1]
    fmt = context.user_data["fmt"]
    await q.edit_message_text(f"⏳ Loading profile: {player}...")

    def _run():
        from ratings.player_ratings import get_player_rating
        from features.player_features import get_batting_stats, get_bowling_stats, get_player_role
        from database.db import get_connection

        rating = get_player_rating(player, fmt)
        batting = get_batting_stats(player, fmt)
        bowling = get_bowling_stats(player, fmt)
        role = get_player_role(player, fmt)
        cf = _cf(fmt)
        conn = get_connection()

        innings = conn.execute(f"""
            SELECT pms.runs, pms.balls_faced, pms.dismissed, pms.fours, pms.sixes,
                   m.date, m.team1, m.team2, pms.team
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.id
            WHERE pms.player_name = ? AND m.match_type = ? AND m.gender = 'male' {cf}
              AND pms.balls_faced > 0
            ORDER BY m.date DESC
            LIMIT 10
        """, (player, fmt)).fetchall()

        bowl_apps = conn.execute(f"""
            SELECT pms.overs_bowled, pms.runs_conceded, pms.wickets, pms.dot_balls,
                   m.date, m.team1, m.team2, pms.team
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.id
            WHERE pms.player_name = ? AND m.match_type = ? AND m.gender = 'male' {cf}
              AND pms.overs_bowled > 0
            ORDER BY m.date DESC
            LIMIT 10
        """, (player, fmt)).fetchall()
        conn.close()
        return rating, batting, bowling, role, [dict(r) for r in innings], [dict(r) for r in bowl_apps]

    rating, batting, bowling, role, innings, bowl_apps = await asyncio.to_thread(_run)

    lines = [
        f"🏏 {player} — {fmt} | {role.title()}",
        f"Games: {rating['games_played']}",
        "",
        "RATINGS",
        f"  Overall     {_bar(rating['overall_rating'])}",
        f"  Batting     {_bar(rating['batting_rating'])}",
        f"  Bowling     {_bar(rating['bowling_rating'])}",
        f"  Form        {_bar(rating['form_score'])}",
        f"  Consistency {_bar(rating['consistency'])}",
    ]

    if batting["innings"] > 0:
        lines += [
            "",
            "CAREER BATTING",
            f"  Innings: {batting['innings']}  |  Runs: {batting['total_runs']:,}",
            f"  Average: {batting['average']:.2f}  |  SR: {batting['strike_rate']:.2f}",
            f"  Highest: {batting['highest']}  |  50s: {batting['fifties']}  |  100s: {batting['hundreds']}",
        ]

    if innings:
        lines += ["", f"RECENT BATTING — Last {len(innings)} innings"]
        for r in innings:
            opp = r["team2"] if r["team"] == r["team1"] else r["team1"]
            sr = round(r["runs"] / r["balls_faced"] * 100, 1) if r["balls_faced"] > 0 else 0
            not_out = "*" if not r["dismissed"] else ""
            lines.append(
                f"  {r['date']}  {r['runs']}{not_out} ({r['balls_faced']}b SR{sr})"
                f"  {r['fours']}x4 {r['sixes']}x6  vs {opp}"
            )
        recent_runs = sum(r["runs"] for r in innings)
        recent_disms = sum(r["dismissed"] for r in innings)
        recent_avg = round(recent_runs / recent_disms, 1) if recent_disms > 0 else recent_runs
        lines.append(f"  Last {len(innings)}: avg {recent_avg}  total {recent_runs} runs")

    if bowling["total_wickets"] > 0:
        lines += [
            "",
            "CAREER BOWLING",
            f"  Wickets: {bowling['total_wickets']}  |  Overs: {bowling['total_overs']:.1f}",
            f"  Economy: {bowling['economy']:.2f}  |  Avg: {bowling['bowling_average']:.2f}",
            f"  SR: {bowling['bowling_strike_rate']:.1f}  |  Dot%: {bowling['dot_pct']:.1f}%",
        ]

    if bowl_apps:
        lines += ["", f"RECENT BOWLING — Last {len(bowl_apps)} appearances"]
        for r in bowl_apps:
            opp = r["team2"] if r["team"] == r["team1"] else r["team1"]
            econ = round(r["runs_conceded"] / r["overs_bowled"], 2) if r["overs_bowled"] > 0 else 0
            lines.append(
                f"  {r['date']}  {r['overs_bowled']:.1f}ov  "
                f"{r['runs_conceded']}r  {r['wickets']}w  econ {econ}  vs {opp}"
            )

    await _send_long(update.effective_chat, "\n".join(lines))
    context.user_data.clear()
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
# FEATURE 3: /team
# ══════════════════════════════════════════════════════════════

async def team_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Select format:", reply_markup=fmt_kbd())
    return TEAM_FMT


async def team_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fmt = q.data
    context.user_data["fmt"] = fmt
    teams = await asyncio.to_thread(_teams, fmt)
    context.user_data["teams"] = teams
    await q.edit_message_text(
        f"Format: {fmt}\nSelect team:",
        reply_markup=list_kbd(teams, 0, "team"),
    )
    return TEAM_SEL


async def team_sel_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select team:",
        reply_markup=list_kbd(context.user_data["teams"], page, "team"),
    )
    return TEAM_SEL


async def team_sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    team = q.data.split("|")[1]
    fmt = context.user_data["fmt"]
    await q.edit_message_text(f"⏳ Analysing {team} ({fmt})...")

    def _run():
        from features.team_features import get_team_recent_form, get_team_squad
        from ratings.player_ratings import get_player_rating
        from models.elo import get_elo

        elo = get_elo(team, fmt)
        form10 = get_team_recent_form(team, fmt, n=10)
        form5 = get_team_recent_form(team, fmt, n=5)
        squad = get_team_squad(team, fmt, last_n_matches=5)[:15]
        ratings = [get_player_rating(p, fmt) for p in squad] if squad else []
        return elo, form10, form5, squad, ratings

    elo, form10, form5, squad, ratings = await asyncio.to_thread(_run)

    form_tag = "Hot" if form10 >= 70 else ("Cold" if form10 <= 30 else "Neutral")
    lines = [
        f"TEAM ANALYSIS — {team} ({fmt})",
        "",
        "OVERVIEW",
        f"  Elo Rating:     {elo:.1f}",
        f"  Form (last 10): {form10:.1f}%  {form_tag}",
        f"  Form (last 5):  {form5:.1f}%",
    ]

    if ratings:
        avg_rat = sum(r["overall_rating"] for r in ratings) / len(ratings)
        sorted_r = sorted(ratings, key=lambda x: x["overall_rating"], reverse=True)
        top3 = sorted_r[:3]
        top_bat = sorted(ratings, key=lambda x: x["batting_rating"], reverse=True)[:3]
        top_bwl = sorted(ratings, key=lambda x: x["bowling_rating"], reverse=True)[:3]

        lines += [
            "",
            f"SQUAD RATINGS (avg {avg_rat:.1f}/100)",
            f"  {'Player':<20} Ovr   Bat   Bowl  Form  G",
            "  " + "─" * 48,
        ]
        for r in sorted_r:
            lines.append(
                f"  {r['player_name']:<20} {r['overall_rating']:4.1f}  "
                f"{r['batting_rating']:4.1f}  {r['bowling_rating']:4.1f}  "
                f"{r['form_score']:4.1f}  {r['games_played']}"
            )

        lines += [
            "",
            "KEY PLAYERS",
            f"  Overall: {', '.join(r['player_name'] for r in top3)}",
            f"  Batting: {', '.join(r['player_name'] for r in top_bat)}",
            f"  Bowling: {', '.join(r['player_name'] for r in top_bwl)}",
        ]

    await _send_long(update.effective_chat, "\n".join(lines))
    context.user_data.clear()
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
# FEATURE 4: /top
# ══════════════════════════════════════════════════════════════

async def top_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Select format:", reply_markup=fmt_kbd())
    return TOP_FMT


async def top_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fmt = q.data
    await q.edit_message_text(f"⏳ Loading top players ({fmt})...")

    def _run():
        from ratings.player_ratings import get_top_players
        return get_top_players(fmt, n=20, role="overall")

    players = await asyncio.to_thread(_run)

    lines = [f"TOP 20 {fmt} PLAYERS", ""]
    lines.append(f"  {'#':<3} {'Player':<22} Ovr   Bat   Bowl  Form  G")
    lines.append("  " + "─" * 55)
    for i, p in enumerate(players, 1):
        lines.append(
            f"  {i:<3} {p['player_name']:<22} {p['overall_rating']:4.1f}  "
            f"{p['batting_rating']:4.1f}  {p['bowling_rating']:4.1f}  "
            f"{p['form_score']:4.1f}  {p['games_played']}"
        )

    await _send_long(update.effective_chat, "\n".join(lines))
    context.user_data.clear()
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
# FEATURE 5: /alerts
# ══════════════════════════════════════════════════════════════

async def alerts_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Select format:", reply_markup=fmt_kbd())
    return ALERTS_FMT


async def alerts_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fmt = q.data
    context.user_data["fmt"] = fmt
    teams = await asyncio.to_thread(_teams, fmt)
    context.user_data["teams"] = teams
    await q.edit_message_text(
        f"Format: {fmt}\nSelect Team 1:",
        reply_markup=list_kbd(teams, 0, "at1"),
    )
    return ALERTS_T1


async def alerts_t1_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select Team 1:",
        reply_markup=list_kbd(context.user_data["teams"], page, "at1"),
    )
    return ALERTS_T1


async def alerts_t1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["t1"] = q.data.split("|")[1]
    await q.edit_message_text(
        f"Team 1: {context.user_data['t1']}\nSelect Team 2:",
        reply_markup=list_kbd(context.user_data["teams"], 0, "at2"),
    )
    return ALERTS_T2


async def alerts_t2_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select Team 2:",
        reply_markup=list_kbd(context.user_data["teams"], page, "at2"),
    )
    return ALERTS_T2


async def alerts_t2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    team1 = context.user_data["t1"]
    team2 = q.data.split("|")[1]
    fmt = context.user_data["fmt"]
    await q.edit_message_text(f"⏳ Analysing {team1} vs {team2}...")

    def _run():
        from models.elo import win_probability
        from features.team_features import get_team_recent_form, get_head_to_head
        return (
            win_probability(team1, team2, fmt) * 100,
            get_team_recent_form(team1, fmt),
            get_team_recent_form(team2, fmt),
            get_head_to_head(team1, team2, fmt),
        )

    elo_prob, form1, form2, h2h = await asyncio.to_thread(_run)
    margin = abs(elo_prob - 50)

    lines = [
        f"SMART ALERTS — {team1} vs {team2} ({fmt})",
        "",
        f"Elo:    {team1} {elo_prob:.1f}%  |  {team2} {100 - elo_prob:.1f}%",
        f"Form:   {team1} {form1:.0f}%  |  {team2} {form2:.0f}%",
    ]
    if h2h["total"] > 0:
        lines.append(f"H2H:    {team1} {h2h['team1_wins']}-{h2h['team2_wins']} {team2}  ({h2h['total']} matches)")

    lines += ["", "SIGNALS"]
    alerts = []

    if margin >= 20:
        winner = team1 if elo_prob >= 50 else team2
        alerts.append(f"HIGH CONFIDENCE: {winner} heavily favored — {max(elo_prob, 100 - elo_prob):.0f}%")
    elif margin >= 10:
        winner = team1 if elo_prob >= 50 else team2
        alerts.append(f"MODERATE EDGE: {winner} has clear Elo advantage")

    if abs(form1 - form2) >= 30:
        in_form = team1 if form1 > form2 else team2
        alerts.append(f"FORM ALERT: {in_form} on strong run — {max(form1, form2):.0f}% last 10")

    if h2h["total"] >= 10 and h2h["team1_win_pct"] >= 65:
        alerts.append(f"H2H DOMINANCE: {team1} wins {h2h['team1_win_pct']:.0f}% historically")
    elif h2h["total"] >= 10 and h2h["team1_win_pct"] <= 35:
        alerts.append(f"H2H DOMINANCE: {team2} dominates this fixture")

    if form1 >= 70 and form2 >= 70:
        alerts.append("BOTH IN FORM: High-quality matchup — close contest expected")

    if margin < 5:
        alerts.append("COIN FLIP: Too close to call — any result possible")

    if not alerts:
        alerts.append("No strong signals. Competitive match with no clear edge.")

    for a in alerts:
        lines.append(f"  ⚡ {a}")

    await q.message.reply_text("\n".join(lines))
    context.user_data.clear()
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
# FEATURE 6: /elo
# ══════════════════════════════════════════════════════════════

async def elo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Select format:", reply_markup=fmt_kbd())
    return ELO_FMT


async def elo_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fmt = q.data
    await q.edit_message_text(f"⏳ Loading {fmt} Elo rankings...")

    def _run():
        from models.elo import get_top_elo_rankings
        return get_top_elo_rankings(fmt, n=20)

    rankings = await asyncio.to_thread(_run)

    if not rankings:
        await q.message.reply_text("No Elo data found.")
        return ConversationHandler.END

    lines = [f"GLOBAL ELO RANKINGS — {fmt}", ""]
    lines.append(f"  {'#':<3} {'Team':<28} Elo")
    lines.append("  " + "─" * 42)
    for i, r in enumerate(rankings, 1):
        bar_len = max(0, int((r["elo"] - 1300) / 800 * 12))
        lines.append(f"  {i:<3} {r['team']:<28} {r['elo']:.1f}  {'█' * bar_len}")

    await q.message.reply_text("\n".join(lines))
    context.user_data.clear()
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
# FEATURE 7: /pvor
# ══════════════════════════════════════════════════════════════

async def pvor_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "PVOR — Player Value Over Replacement\n"
        "Measures how much a player increases win probability.\n\n"
        "Select format:",
        reply_markup=fmt_kbd(),
    )
    return PVOR_FMT


async def pvor_fmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fmt = q.data
    context.user_data["fmt"] = fmt
    teams = await asyncio.to_thread(_teams, fmt)
    context.user_data["teams"] = teams
    await q.edit_message_text(
        f"Format: {fmt}\nSelect player's team:",
        reply_markup=list_kbd(teams, 0, "pvteam"),
    )
    return PVOR_TEAM


async def pvor_team_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select player's team:",
        reply_markup=list_kbd(context.user_data["teams"], page, "pvteam"),
    )
    return PVOR_TEAM


async def pvor_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    team = q.data.split("|")[1]
    fmt = context.user_data["fmt"]
    context.user_data["team"] = team
    players = await asyncio.to_thread(_players, team, fmt)
    context.user_data["players"] = players
    await q.edit_message_text(
        f"Team: {team}\nSelect player:",
        reply_markup=list_kbd(players, 0, "pvplayer"),
    )
    return PVOR_PLAYER


async def pvor_player_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select player:",
        reply_markup=list_kbd(context.user_data["players"], page, "pvplayer"),
    )
    return PVOR_PLAYER


async def pvor_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    player = q.data.split("|")[1]
    context.user_data["player"] = player
    await q.edit_message_text(
        f"Player: {player}\nSelect opponent team:",
        reply_markup=list_kbd(context.user_data["teams"], 0, "pvopp"),
    )
    return PVOR_OPP


async def pvor_opp_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    await q.edit_message_text(
        "Select opponent:",
        reply_markup=list_kbd(context.user_data["teams"], page, "pvopp"),
    )
    return PVOR_OPP


async def pvor_opp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    opponent = q.data.split("|")[1]
    player = context.user_data["player"]
    team = context.user_data["team"]
    fmt = context.user_data["fmt"]

    await q.edit_message_text(
        f"⏳ Computing PVOR for {player}...\n(runs ~2000 simulations — takes ~15s)"
    )

    def _run():
        from impact.pvor import compute_pvor
        return compute_pvor(player, team, opponent, fmt)

    result = await asyncio.to_thread(_run)

    stars = {
        "Elite": "★★★★★", "High": "★★★★☆",
        "Medium": "★★★☆☆", "Low": "★★☆☆☆", "Negative": "★☆☆☆☆",
    }
    lines = [
        f"PVOR — {result['player']}",
        f"{team} vs {opponent} ({fmt})",
        "",
        f"Win WITH    {result['player']}: {result['win_with']:.1f}%",
        f"Win WITHOUT {result['player']}: {result['win_without']:.1f}%",
        "",
        f"PVOR:   {result['pvor']:+.2f}%",
        f"Impact: {result['impact_label']}  {stars.get(result['impact_label'], '')}",
    ]

    await q.message.reply_text("\n".join(lines))
    context.user_data.clear()
    return ConversationHandler.END




# ══════════════════════════════════════════════════════════════
# WIRE UP
# ══════════════════════════════════════════════════════════════

def build_app() -> Application:
    app = Application.builder().token(TOKEN).build()

    # /start + /help
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # /predict
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("predict", predict_start)],
        states={
            PREDICT_FMT: [CallbackQueryHandler(predict_fmt, pattern="^(T20|ODI)$")],
            PREDICT_T1: [
                CallbackQueryHandler(predict_t1_page, pattern=r"^pt1_pg\|"),
                CallbackQueryHandler(predict_t1, pattern=r"^pt1\|"),
            ],
            PREDICT_T2: [
                CallbackQueryHandler(predict_t2_page, pattern=r"^pt2_pg\|"),
                CallbackQueryHandler(predict_t2, pattern=r"^pt2\|"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        per_user=True,
    ))

    # /player
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("player", player_start)],
        states={
            PLAYER_FMT: [CallbackQueryHandler(player_fmt, pattern="^(T20|ODI)$")],
            PLAYER_TEAM: [
                CallbackQueryHandler(player_team_page, pattern=r"^plteam_pg\|"),
                CallbackQueryHandler(player_team, pattern=r"^plteam\|"),
            ],
            PLAYER_SEL: [
                CallbackQueryHandler(player_sel_page, pattern=r"^plsel_pg\|"),
                CallbackQueryHandler(player_sel, pattern=r"^plsel\|"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        per_user=True,
    ))

    # /team
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("team", team_start)],
        states={
            TEAM_FMT: [CallbackQueryHandler(team_fmt, pattern="^(T20|ODI)$")],
            TEAM_SEL: [
                CallbackQueryHandler(team_sel_page, pattern=r"^team_pg\|"),
                CallbackQueryHandler(team_sel, pattern=r"^team\|"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        per_user=True,
    ))

    # /top
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("top", top_start)],
        states={
            TOP_FMT: [CallbackQueryHandler(top_fmt, pattern="^(T20|ODI)$")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        per_user=True,
    ))

    # /alerts
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("alerts", alerts_start)],
        states={
            ALERTS_FMT: [CallbackQueryHandler(alerts_fmt, pattern="^(T20|ODI)$")],
            ALERTS_T1: [
                CallbackQueryHandler(alerts_t1_page, pattern=r"^at1_pg\|"),
                CallbackQueryHandler(alerts_t1, pattern=r"^at1\|"),
            ],
            ALERTS_T2: [
                CallbackQueryHandler(alerts_t2_page, pattern=r"^at2_pg\|"),
                CallbackQueryHandler(alerts_t2, pattern=r"^at2\|"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        per_user=True,
    ))

    # /elo
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("elo", elo_start)],
        states={
            ELO_FMT: [CallbackQueryHandler(elo_fmt, pattern="^(T20|ODI)$")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        per_user=True,
    ))

    # /pvor
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("pvor", pvor_start)],
        states={
            PVOR_FMT: [CallbackQueryHandler(pvor_fmt, pattern="^(T20|ODI)$")],
            PVOR_TEAM: [
                CallbackQueryHandler(pvor_team_page, pattern=r"^pvteam_pg\|"),
                CallbackQueryHandler(pvor_team, pattern=r"^pvteam\|"),
            ],
            PVOR_PLAYER: [
                CallbackQueryHandler(pvor_player_page, pattern=r"^pvplayer_pg\|"),
                CallbackQueryHandler(pvor_player, pattern=r"^pvplayer\|"),
            ],
            PVOR_OPP: [
                CallbackQueryHandler(pvor_opp_page, pattern=r"^pvopp_pg\|"),
                CallbackQueryHandler(pvor_opp, pattern=r"^pvopp\|"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        per_user=True,
    ))

    return app


def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)
    print("CricketIQ Bot starting...")
    app = build_app()
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
