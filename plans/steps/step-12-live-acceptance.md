# Step 12 — 60s live acceptance (pipeline core gate)

phase: net · machine: laptop · depends: step-11

## Goal
One battery of commands proves the whole pipeline: stream → filter → score → log → resume-safe → replay-consistent. This is the gate to the UI phase. Nothing in Steps 13+ starts until every check here passes.

## Do
Run the acceptance battery exactly as written and capture all output.

## Accept (ALL must pass)
```bash
# 1) live run
python -m laya_sort.jetstream --seconds 60
# 2) log populated
wc -l data/decisions.jsonl
# 3) replay cross-check
python scripts/replay.py --in data/decisions.jsonl --out data/replay_check.jsonl
python - <<'EOF'
import json
live = [json.loads(l) for l in open("data/decisions.jsonl") if l.strip()]
re   = [json.loads(l) for l in open("data/replay_check.jsonl") if l.strip()]
key = lambda d: (d["uri"], d["verdict"], json.dumps(d["probabilities"], sort_keys=True))
assert [key(x) for x in live] == [key(x) for x in re], "verdict drift between live and replay!"
print("REPLAY MATCH", len(live))
EOF
# 4) no duplicate ordering keys (Step 11 check, re-run)
```
- Final report of the live run shows latency p50 + p90 and all counters.
- `REPLAY MATCH <n>` printed, where n equals the log line count.
- No duplicate `seq`; cursor file advanced.

## Do NOT
- Start the UI phase (Step 13) with any failed check — report which one failed and stop.
- "Fix" a failed replay-match by editing old log lines. The log is append-only history.
