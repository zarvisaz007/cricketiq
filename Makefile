# CricketIQ — Makefile
# Run `make help` to see all commands.

.PHONY: help setup download ingest ratings train run clean reset

help:
	@echo ""
	@echo "  CricketIQ Commands"
	@echo "  ────────────────────────────────"
	@echo "  make setup      Full first-time setup (all steps)"
	@echo "  make install    Install Python dependencies"
	@echo "  make db         Initialize SQLite database"
	@echo "  make download   Download Cricsheet match data"
	@echo "  make ingest     Load data into database"
	@echo "  make ratings    Compute player ratings"
	@echo "  make train      Train all ML models"
	@echo "  make run        Launch the CLI tester"
	@echo "  make clean      Remove trained models"
	@echo "  make reset      Wipe DB and start fresh"
	@echo ""

# ── Full first-time setup ────────────────────────────────────
setup: install db download ingest ratings train
	@echo ""
	@echo "  Setup complete. Run: make run"

# ── Individual steps ─────────────────────────────────────────
install:
	pip3 install -r requirements.txt

db:
	python3 scripts/setup_db.py

download:
	python3 scripts/download_data.py

ingest:
	python3 backend/data/ingestion.py

ratings:
	python3 backend/ratings/player_ratings.py

train:
	python3 backend/models/train_all.py

run:
	python3 frontend/test_cli.py

# ── Maintenance ───────────────────────────────────────────────
clean:
	rm -f backend/models/*.pkl backend/models/*.json backend/models/*.ubj

reset: clean
	rm -f database/cricketiq.db
	python3 scripts/setup_db.py
	@echo "Database reset. Run: make ingest"
