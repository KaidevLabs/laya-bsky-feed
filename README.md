Laya Sky Feed

## Run

Terminal A — pipeline + web server:
    source .venv/bin/activate
    LAYA_DEVICE=cpu python -m laya_sort.daemon

Terminal B — the terminal view:
    tail -f data/decisions.jsonl

Browser: http://127.0.0.1:8000
