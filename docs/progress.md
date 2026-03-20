# Progress — CricketIQ

Update this file after completing each task.
Format: [x] = done, [ ] = pending, [~] = in progress

---

## Phase 0: Project Setup

- [x] Folder structure created
- [x] README.md written
- [x] .env.example created
- [x] .gitignore created
- [x] requirements.txt created
- [x] All docs files created
- [x] All agent files created

---

## Phase 1: Data Layer

- [ ] Download Cricsheet IPL data
- [ ] Download Cricsheet T20I data
- [ ] Download Cricsheet ODI data
- [ ] Run `python scripts/setup_db.py` — initialize DB
- [ ] Run `python data/ingestion.py` — load all data
- [ ] Verify: match count > 1000 in DB
- [ ] Verify: player_match_stats populated

---

## Phase 2: Ratings

- [ ] Run `python ratings/player_ratings.py`
- [ ] Verify: top batsmen have rating > 75
- [ ] Run `python models/elo.py` — build Elo rankings
- [ ] Verify: India/Australia/England in top 10

---

## Phase 3: Models

- [ ] Run `python models/train_all.py`
- [ ] Verify: Logistic model saved (models/logistic_T20.pkl)
- [ ] Verify: XGBoost model saved (models/xgb_T20.pkl)
- [ ] Check: val accuracy > 55% for both

---

## Phase 4: CLI Testing

- [ ] Run `python test_cli.py`
- [ ] Test: India vs Australia T20 prediction
- [ ] Test: Virat Kohli player rating
- [ ] Test: Bumrah PVOR score
- [ ] Test: Player report (with/without OpenRouter key)
- [ ] Test: Smart alerts
- [ ] Test: Top 15 T20 batsmen

---

## Phase 5: Post-MVP (Telegram Bot)

- [ ] Create Telegram bot via BotFather
- [ ] Add TELEGRAM_BOT_TOKEN to .env
- [ ] Implement bot/handlers.py
- [ ] Test all commands on Telegram
- [ ] Deploy to server (Railway / DigitalOcean)

---

## Known Issues

_Log bugs here as discovered._

---

## Last Updated

2026-03-20 — Project initialized.
