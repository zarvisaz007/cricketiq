# CricketIQ v2 — Makefile
# Run `make help` to see all commands.

.PHONY: help setup download ingest ratings train run clean reset \
        migrate migrate-002 seed-venues train-ipl live fantasy bot retrain schedule

help:
	@echo ""
	@echo "  CricketIQ v2 Commands"
	@echo "  ────────────────────────────────"
	@echo "  make setup      Full first-time setup (all steps)"
	@echo "  make install    Install Python dependencies"
	@echo "  make db         Initialize SQLite database"
	@echo "  make migrate    Run v2 schema migration"
	@echo "  make seed-venues Seed venue data"
	@echo "  make download   Download Cricsheet match data"
	@echo "  make ingest     Load data into database"
	@echo "  make ratings    Compute player ratings"
	@echo "  make train      Train all ML models"
	@echo "  make train-ipl  Train IPL-specific model"
	@echo "  make run        Launch the CLI"
	@echo "  make live       Start live score poller"
	@echo "  make fantasy    Show Dream11 team builder (via CLI)"
	@echo "  make bot        Start Telegram bot"
	@echo "  make schedule   Scrape upcoming match schedule"
	@echo "  make migrate-002 Run upcoming_matches migration"
	@echo "  make retrain    Run nightly retrain script"
	@echo "  make clean      Remove trained models"
	@echo "  make reset      Wipe DB and start fresh"
	@echo ""

# ── Full first-time setup ────────────────────────────────────
setup: install db migrate seed-venues download ingest ratings train train-ipl
	@echo ""
	@echo "  Setup complete. Run: make run"

# ── Individual steps ─────────────────────────────────────────
install:
	pip3 install -r requirements.txt

db:
	python3 scripts/setup_db.py

migrate:
	python3 database/migrations/001_schema_v2.py
	python3 database/migrations/002_upcoming_matches.py

migrate-002:
	python3 database/migrations/002_upcoming_matches.py

seed-venues:
	python3 database/seed_venues.py

download:
	python3 scripts/download_data.py

ingest:
	python3 backend/data/ingestion.py

ratings:
	python3 backend/ratings/player_ratings.py

train:
	python3 backend/models/train_all.py

train-ipl:
	python3 backend/models/ipl_predictor.py

run:
	python3 frontend/test_cli.py

live:
	python3 backend/scrapers/live_poller.py

bot:
	python3 bot/main.py

schedule:
	python3 backend/scrapers/cricbuzz_schedule.py

retrain:
	python3 scripts/nightly_retrain.py

# ── Maintenance ───────────────────────────────────────────────
clean:
	rm -f backend/models/*.pkl backend/models/*.json backend/models/*.ubj models/*.pkl

reset: clean
	rm -f database/cricketiq.db
	python3 scripts/setup_db.py
	python3 database/migrations/001_schema_v2.py
	python3 database/migrations/002_upcoming_matches.py
	python3 database/seed_venues.py
	@echo "Database reset. Run: make ingest"
