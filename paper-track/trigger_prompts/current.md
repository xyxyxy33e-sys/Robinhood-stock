# Live Routine prompts (source of record) — from 2026-10-08

These are the exact prompts of the three Agentic Routines. The procedure itself
lives in `RUNBOOK.md`; keep these short. Schedules use `CRON_TZ=America/New_York`.
Pre-switch prompts: `archive-2026-10-08/`.

## Trade run — `CRON_TZ=America/New_York 50 15 * * 1-5`

Trade run for the Robinhood Agentic account 576391551 (repo xyxyxy33e-sys/Robinhood-stock, branch claude/robinhood-portfolio-builder-p3efca, clone at /home/user/Robinhood-stock — clone it if missing). Run `git pull --ff-only`, then follow RUNBOOK.md sections 0 and 1 exactly: three data calls, write data/runs/in/<today>.json, run `python3 paper-track/live_run.py signal data/runs/in/<today>.json`, and place exactly the orders it prints, sells first, finishing before 15:59 ET (VIXM is regular-hours only). Exit 3 = market closed: stop. Exit 2 = a guard tripped: do not trade, report it. Do nothing else in this window: no reading STRATEGY.md, no research, no commentary. Never edit code, docs or Routines from this run.

## Post-close run — `CRON_TZ=America/New_York 10 16 * * 1-5`

Post-close run for the Robinhood Agentic account 576391551 (repo xyxyxy33e-sys/Robinhood-stock, branch claude/robinhood-portfolio-builder-p3efca, clone at /home/user/Robinhood-stock). Run `git pull --ff-only`, then follow RUNBOOK.md sections 0 and 2 exactly: holiday check; `live_run.py status` and the fallback if the 15:50 run did not complete (lose the overnight, never the signal; VIXM waits for the next open); `live_run.py record`; on Fridays the weekly report entry and the Top-N paper mark; the dashboard update; exactly ONE push; commit data/. Never override a guard, and never edit code, docs or Routines from this run.

## Monthly check — `CRON_TZ=America/New_York 0 10 1 * *`

Monthly live-vs-strategy reconciliation for the Robinhood Agentic account 576391551 (repo xyxyxy33e-sys/Robinhood-stock, branch claude/robinhood-portfolio-builder-p3efca). Run `git pull --ff-only`, then follow RUNBOOK.md section 3. Diagnostic only: report, change nothing. If the Robinhood tools are unavailable, skip silently; next month's check will try again.
