# Step 07 — replay.py: offline re-scoring + determinism proof

phase: core · machine: laptop · depends: step-06

## Goal
The A/B workhorse: re-score any saved posts file offline (no network), deterministically.

## Do
1. Factor the input parsing out of the CLI into `laya_sort/cli.py::read_posts(path) -> list[dict]` (handles JSON array and JSONL; shared by CLI and replay).
2. Create `scripts/replay.py`:
   - args: `--in <posts.json|posts.jsonl>` (required), `--out <verdicts.jsonl>` (required).
   - Reads posts via `read_posts`, scores via `laya.score()`, writes verdicts to `--out` (one JSON per line, no timestamps — score() already guarantees that).

## Files
- create `scripts/replay.py`
- edit `laya_sort/cli.py` (extract `read_posts`; behavior unchanged)

## Accept
```bash
python scripts/replay.py --in fixtures/posts_v1.json --out data/replay_a.jsonl
python scripts/replay.py --in fixtures/posts_v1.json --out data/replay_b.jsonl
diff data/replay_a.jsonl data/replay_b.jsonl && echo DETERMINISTIC
```
Prints `DETERMINISTIC`. The two files are byte-identical.

## Do NOT
- Add any network call, model reload per post (the agent singleton must load once), or timestamp to replay.
- Proceed if `diff` shows any difference — determinism is the property Step 12's live check depends on; report and stop.
