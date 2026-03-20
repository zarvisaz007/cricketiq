# Agent Rules — CricketIQ

All agents must follow these rules without exception.
These rules exist to prevent contradiction and duplication across sessions.

---

## Universal Rules (All Agents)

1. **Documentation is truth.** If it's not in /docs, it doesn't exist.
2. **Never rely on chat memory.** Every session starts from docs/session-start.md.
3. **Update progress.md** after completing any task.
4. **Log decisions in decisions.md** before implementing anything significant.
5. **Never hardcode credentials.** Use .env only.
6. **Do not touch files outside your defined scope.**
7. **Add to change-log.md** after any code change.
8. **Ask before changing architecture** — write the proposal in decisions.md first.

---

## Data Agent

**Scope:** data/, database/, scripts/
**Reads first:** architecture.md, data-model.md
**Forbidden:** models/, simulation/, bot/, nlp/

**Responsibilities:**
- Parse and ingest Cricsheet data
- Maintain SQLite schema
- Handle data normalization
- Write and run ingestion scripts

---

## Model Agent

**Scope:** models/, ratings/, features/
**Reads first:** architecture.md, api-contract.md, data-model.md
**Forbidden:** data/ingestion.py, bot/, simulation/ (read-only)

**Responsibilities:**
- Implement and train Elo, Logistic, XGBoost models
- Compute player ratings
- Build feature engineering functions
- Save trained models to models/*.pkl

---

## Simulation Agent

**Scope:** simulation/, impact/
**Reads first:** architecture.md, api-contract.md
**Forbidden:** data/, models/ (read-only access only), database/ (read-only)

**Responsibilities:**
- Monte Carlo match simulation
- PVOR player impact computation
- Only calls ratings and features — never modifies them

---

## Reviewer Agent

**Scope:** All files (read-only)
**Reads first:** api-contract.md, progress.md, change-log.md
**Forbidden:** Write to any code file

**Responsibilities:**
- Verify that module outputs match api-contract.md
- Check that progress.md reflects actual state of code
- Flag inconsistencies between docs and implementation
- Suggest updates to memory.md if outdated

---

## Output Standards

All prediction functions must:
- Return `dict` (not print directly)
- Use percentage (0–100) not decimal (0–1) for probabilities
- Handle missing data gracefully (return defaults, no crashes)
- Be callable from test_cli.py without modification
