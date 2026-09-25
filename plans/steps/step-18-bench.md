# Step 18 — bench: GPU fp16 vs CPU on the same box

phase: gpu · machine: desktop · depends: step-17

## Goal
Real wall-clock numbers. The "fast demo" claim lives or dies here — medians only, no proxies.

## Do
1. Create `scripts/bench.py`:
   - Post set: 10 posts, fixed (the 3 fixtures repeated to 10, or 10 captured live — either, but the SAME set for both devices).
   - `for device in ["cuda", "cpu"]`: fresh agent per device (`laya_sort.laya` singleton is per-process — either re-import in a subprocess per device or parameterize `get_agent(device)`; simplest correct: run the bench script twice via env var and merge, or clear the singleton between phases).
   - Per device: 2 warmup scores (excluded), then score the 10 posts ≥ 1 full pass ×5 repetitions, recording per-score wall-clock with `time.perf_counter()`.
   - Print one table: `device | n | p50_ms | p90_ms | implied_posts_per_s (= 1000/p50)`.
   - Also save the table to `data/bench_results.json`.
2. Report honestly: warmup excluded but stated; medians + p90 only.

## Files
- create `scripts/bench.py`

## Accept
```bash
LAYA_DEVICE=cuda python scripts/bench.py
```
- Both device rows printed with ≥10 samples each. Gate: **GPU p50 ≤ 50 ms/post**.
- CPU row recorded as the baseline (expected: ~200–460 ms/post per the vendor README — your numbers replace the folklore).
- If GPU p50 > 50 ms: report the table and STOP. The "fast" claim dies; do not tune, do not lower the bar.

## Do NOT
- Report means, best-of, or load-time-excluded numbers.
- Mix post sets between devices.
- Run bench while the daemon is scoring (contended GPU = lying numbers).
