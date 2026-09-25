# Step 13 — daemon: FastAPI + SSE /stream + /history + README runbook

phase: ui · machine: laptop · depends: step-12

## Goal
The single long-running process: scores the live stream AND serves the log to viewers. Plus the README runbook (decision D11).

## Do
1. Create `laya_sort/daemon.py`:
   - FastAPI app; lifespan starts the Step-10 consumer task — same code path as `python -m laya_sort.jetstream`, but without `--seconds` (runs until stopped). Do NOT duplicate the consumer logic; refactor it into a callable if needed and make the `--seconds` entry point use the same callable.
   - `GET /` → `FileResponse("dashboard/index.html")`.
   - `GET /stream` → `StreamingResponse(media_type="text/event-stream")`: tail `config.LOG_PATH` starting at the current end-of-file at connect time; poll for new bytes every 250 ms; for each complete new line emit `data: <line>\n\n`; emit `: ping\n\n` every 15 s to keep intermediaries alive.
   - `GET /history?n=20` → last N lines of the log as `{"items": [...]}`; clamp n to 1..100.
   - `main()` = `uvicorn.run(app, host="127.0.0.1", port=config.PORT)`.
2. Update `README.md` with the runbook section (exactly the D11 deliverable):
```markdown
## Run

Terminal A — pipeline + web server:
    source .venv/bin/activate
    LAYA_DEVICE=cpu python -m laya_sort.daemon

Terminal B — the terminal view:
    tail -f data/decisions.jsonl

Browser: http://127.0.0.1:8000
```

## Files
- create `laya_sort/daemon.py`
- edit `README.md` (runbook section only — leave the rest alone)

## Accept
```bash
python -m laya_sort.daemon &
sleep 20    # let it score some posts
curl -s "http://127.0.0.1:8000/history?n=5"              # JSON with ≥1 item
curl -sN --max-time 10 "http://127.0.0.1:8000/stream"    # "data: {...}" lines arriving live
curl -s "http://127.0.0.1:8000" | head -3                # HTML served
```
All four behave as specified; the consumer keeps scoring while /stream clients sit attached.

## Do NOT
- Bind to 0.0.0.0, add auth, or add frameworks — localhost-only by design (D9/D11).
- Serve SSE by re-reading the whole log each poll — tail from a byte offset.
- Block the event loop: consumer stays on `asyncio.to_thread` (Step 10 pattern).
