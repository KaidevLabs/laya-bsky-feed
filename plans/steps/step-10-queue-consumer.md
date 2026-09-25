# Step 10 — bounded queue + scoring consumer

phase: net · machine: laptop · depends: step-09, step-05

## Goal
Reader and scorer decoupled: the WS loop never blocks on model inference; the queue is bounded; backpressure drops are counted, not hidden.

## Do
1. In `laya_sort/jetstream.py`:
   - `asyncio.Queue(maxsize=config.QUEUE_MAX)`. The reader task pushes `(recv_monotonic, post_dict)`. If the queue is full: drop the incoming event, increment `dropped_backpressure` — never await on a full queue, never block the WS read loop.
   - Consumer task: pops an item, runs `await asyncio.to_thread(laya.score, post)` (score is blocking torch work — it must NOT run on the event loop), computes `latency_ms = (time.monotonic() - recv_monotonic) * 1000`, appends the verdict + `latency_ms` + a `scored_at` wall-clock timestamp to `config.LOG_PATH` (open in append mode, `f.write(json.dumps(rec) + "\n")`, flush per line). Record the latency in a list for the report.
   - Every 10s print one status line: `queue=<depth> seen=.. kept=.. dropped_bp=.. scored=.. p50_lat_ms=..` (stderr, so a piped stdout stays clean).
   - Entry point: `python -m laya_sort.jetstream --seconds N` — runs reader+consumer for N seconds, prints a final report (all counters + latency median/p90 + scored count), exits 0.
2. Ensure `data/` exists before the first append (`Path.mkdir(parents=True, exist_ok=True)`).

## Files
- edit `laya_sort/jetstream.py`

## Accept
```bash
python -m laya_sort.jetstream --seconds 60
wc -l data/decisions.jsonl
```
- Status lines every ~10s; final report has all counters + latency stats.
- `scored == kept - dropped_backpressure` (±1 for the final second), and the log line count equals `scored`.

## Do NOT
- Run `score()` directly on the event loop (it would freeze the WS reader — that is exactly what `asyncio.to_thread` prevents).
- Retry a failed `score()` more than once; count failures as `score_errors` and keep going.
- Buffer without bound or "remember" dropped events.
