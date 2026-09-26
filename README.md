Laya Sky Feed

## Run

Terminal A — pipeline + web server:
    source .venv/bin/activate
    LAYA_DEVICE=cpu python -m laya_sort.daemon

Terminal B — the terminal view:
    tail -f data/decisions.jsonl

Browser: http://127.0.0.1:8000

## Raw stream playground (no model, no pipeline)

A standalone page — the browser connects to Jetstream directly; the whole post
stream comes in raw and a live regex splits it green (match) / red (discarded).
Editing the regex re-evaluates the last 1000 posts instantly. No backend needed:

    python3 -m http.server 8088 --directory dashboard
    # then open http://localhost:8088/stream.html
    # (or just open dashboard/stream.html as a file)

Keys: `/` focuses the regex, space pauses, empty regex accepts everything.

