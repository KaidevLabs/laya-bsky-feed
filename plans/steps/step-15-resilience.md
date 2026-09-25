# Step 15 — resilience: kill/restart mid-stream, nothing lost

phase: ui · machine: laptop · depends: step-14

## Goal
Prove the D10 property: the log is the source of truth; the daemon and the page are replaceable viewers. Manual procedure — run it exactly, check every box.

## Do (procedure)
1. Terminal A: start the daemon. Terminal B: `tail -f data/decisions.jsonl`. Browser: open the page.
2. After ~30s: Ctrl+C the daemon. Expected: the browser keeps retrying (EventSource native behavior) and the page simply stops receiving new cards.
3. Restart the daemon with the same command. Within ~5s: `tail -f` shows fresh lines again, and the browser resumes live updates WITHOUT a manual reload.
4. Reload the browser page: history renders, then live continues.
5. Re-run the duplicate-check from Step 11 on the log.
6. Read `README.md`'s runbook and confirm it matches exactly what you just did — if any command drifted, fix the README now.

## Accept (checklist — every box)
- [ ] Browser resumes live updates without manual reload after the daemon restart
- [ ] `tail -f` output is continuous across the restart
- [ ] No duplicate `seq` in `data/decisions.jsonl`
- [ ] `data/cursor.json` advanced across the restart
- [ ] README runbook matches reality
- [ ] During the daemon-down window, no verdicts were lost once it returned (the stream simply continued from the cursor)

## Do NOT
- Add JS reconnect logic — EventSource already does this; if it doesn't resume, the bug is server-side (SSE generator). Report it.
- "Recover" lost time by re-scoring from scratch — the cursor is the only resume mechanism.
