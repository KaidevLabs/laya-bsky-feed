# Step 11 — cursor resume + reconnect + dedupe

phase: net · machine: laptop · depends: step-10

## Goal
Daemon-grade reader: survives disconnects, resumes from the last processed event, never double-counts.

## Do
1. On every successful append, atomically persist `config.CURSOR_PATH` as `{"seq": <last seq>, "time_us": <last time_us>}` — write to `<path>.tmp` then `os.replace`. Field names = whatever Step 08 actually observed (adjust if Jetstream names them differently, and say so in the report).
2. Wrap the WS loop in a retry: on disconnect, reconnect after backoff 1s → 2s → 4s → … capped at 30s. If a cursor file exists, append `?cursor=<last time_us>` to the URL.
3. Dedupe: skip any message whose ordering key (`seq`) is ≤ the last persisted one. Log skips at debug level only.
4. Print `reconnect after Ns, resuming from seq=<..>` on every reconnect.

## Files
- edit `laya_sort/jetstream.py`

## Accept
```bash
# terminal 1 — start, wait ~20s, then Ctrl+C:
python -m laya_sort.jetstream --seconds 45
# immediately restart:
python -m laya_sort.jetstream --seconds 45
# then verify no duplicates:
python - <<'EOF'
import json
seqs = [json.loads(l)["seq"] for l in open("data/decisions.jsonl") if l.strip()]
assert len(seqs) == len(set(seqs)), "duplicate seq!"
print("NO DUPES", len(seqs))
EOF
```
Prints `NO DUPES <n>`; the log shows a clean continuation (seq increases across the restart, no reset to earlier values).

## Do NOT
- Trust the cursor blindly across long gaps — Jetstream retention is finite. If the reconnect is rejected or produces nothing for >60s, fall back to a fresh connection without cursor, print a warning, and continue (fresh events still flow).
- Let a reconnect storm (rapid failures) spin without backoff.
