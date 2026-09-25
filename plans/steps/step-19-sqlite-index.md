# Step 19 — SQLite ranking index (derived from the log)

phase: feed · machine: laptop · depends: step-12 (needs a populated log) · may run before/parallel to GPU steps

## Goal
A disposable, rebuildable index for ranked queries — the D6/D10 split made concrete. The log stays the source of truth.

## Do
1. Create `laya_sort/store.py`:
   - `build_index(log_path=config.LOG_PATH, db_path="data/feed.sqlite")`:
     - `CREATE TABLE IF NOT EXISTS posts(uri TEXT PRIMARY KEY, cid TEXT, author TEXT, text TEXT, langs TEXT, created_at TEXT, verdict TEXT, confidence REAL, probabilities TEXT, scored_at TEXT)`
     - one `INSERT OR REPLACE` per log line (probabilities as JSON string)
     - then `CREATE INDEX IF NOT EXISTS idx_conf ON posts(confidence DESC)`
   - Idempotent: running twice yields the same row count, no error.
   - `top(n)` → rows ordered by `confidence DESC`, `created_at DESC` tiebreak, filtered to `verdict == "A"`.
2. Fill the two CLI stubs from Step 06:
   - `python -m laya_sort.cli build-index` → calls `build_index`, prints row count.
   - `python -m laya_sort.cli top [--n 10]` → prints n rows (uri, verdict, confidence, first 60 chars of text).

## Files
- create `laya_sort/store.py`
- edit `laya_sort/cli.py` (fill the two stubs — nothing else)

## Accept
```bash
python -m laya_sort.cli build-index
python -m laya_sort.cli build-index        # second run: same count, no error
python -m laya_sort.cli top --n 10         # rows sorted by confidence DESC
```

## Do NOT
- Treat the DB as the source of truth — it may be deleted and rebuilt from the log at any time (that is the definition of "derived").
- Add update-in-place logic from the live stream here — the index is batch-built from the log (live mirroring is a later concern, out of MVP scope).
