# Session Start — CricketIQ

**Read this first. Every session. No exceptions.**

---

## Step 1: Load Context (2 minutes)

Read these files in order:

1. `docs/memory.md` — compact project summary (read this NOW)
2. `docs/progress.md` — what's done and what's next
3. `docs/agent-rules.md` — how you must behave

---

## Step 2: Identify Your Role

Determine which agent you are for this session:

| If you're working on... | Agent | Name |
|------------------------|-------|------|
| backend/, database/, scripts/ | Backend Agent | NOVA |
| frontend/, bot/ | Frontend Agent | ATLAS |
| Makefile, orchestrator, deployment | Infra Agent | FORGE |
| Review and validation | Reviewer Agent | LENS |

Read your agent file in `agents/` before starting.

---

## Step 3: Find Next Task

Open `docs/progress.md` and find the first `[ ]` unchecked item.
That is your next task.

---

## Step 4: Work

- Write code in your agent's scope only
- Test your changes
- Update `docs/progress.md` (check off completed tasks)
- Log your change in `docs/change-log.md`

---

## Step 5: End of Session

Before finishing:
1. Update `docs/progress.md`
2. Add entry to `docs/change-log.md`
3. Update `docs/memory.md` if project context has changed

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `make setup` | Full first-time setup (all steps) |
| `make run` | Launch CLI tester |
| `make reset` | Wipe DB and restart |
| `python3 scripts/orchestrator.py` | Run full pipeline automatically |
| `python3 scripts/orchestrator.py --from ingest` | Resume from a step |
| `python3 frontend/test_cli.py` | Interactive CLI tester |

---

## Current Status

See `docs/progress.md` for exact current state.

Phase 0 (Setup) is complete.
Phase 1 (Data ingestion) is next.
