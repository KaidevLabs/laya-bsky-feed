Laya Sky Feed

A Bluesky feed pipeline that runs on your own hardware: the Jetstream firehose
is consumed, pre-filtered, scored in-process by the Laya RL agent, and logged
append-only to `data/decisions.jsonl`. A FastAPI daemon serves the live feed
and a single-file dashboard.

## Demo

https://github.com/user-attachments/assets/0e77137a-1b7b-43ee-b276-b63f318d3a7e

*15s teaser, plays inline. Full 61s recording: [demo-stream.mp4](demo-stream.mp4) ·
[demo-stream.webm](demo-stream.webm). Recorded from the real page against the
real firehose: the regex is typed live, the meaning tab scores a 5/s sample
with Laya, and the collect threshold is relaxed from 95% to 80% on camera when
the confident drip slows. The capture choreography (CDP screencast of headless
chromium) stays scratch; only its outputs are committed.*

## Setup

Prereqs: **Python ≥ 3.10** (developed on 3.14), git. **No API keys** — the
model is a public Hugging Face checkpoint and Jetstream needs no auth.

    git clone https://github.com/<you>/laya-sky-feed.git
    cd laya-sky-feed
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    pip install torch        # CPU; on the RTX 5090 box use the cu128 index instead (see requirements.txt)
    hf download convaiinnovations/laya --local-dir models/laya

The last step downloads the model (~2.3 GB: `model.safetensors` + encoder +
tokenizer + the vendor `rl_agent_*.py` files) into `models/laya/`. Everything
the pipeline writes (`data/`) and the venv are gitignored; nothing in this
repo references personal paths, and no credentials are needed anywhere.

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

## Meaning mode (Laya in the playground)

Same page, second tab: switch to **meaning** and posts get scored by the model
on an arbitrary "pick one" question you type (topic, sentiment, ask/tell, …).
The whole stream still flows gray; a sample (default 2/s) is pre-filtered and
sent to a tiny local scoring server that reuses the vendor agent:

    source .venv/bin/activate
    python scripts/meaning_server.py        # 127.0.0.1:8100, loads models/laya

Cards start amber-pulsing (queued) and flip to their option's color the moment
the verdict lands; the sidebar tallies options live. Unsure-verdicts (below the
confidence slider) render dashed. `↺ backfill` scores the buffered last 300
posts with the current question. On CPU expect ~200ms/post (raise the sample
rate on the 5090); the regex tab keeps working with or without the backend.


