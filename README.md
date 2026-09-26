Laya Sky Feed

## Demo

![Laya stream playground — live firehose, regex split, meaning verdicts and the reading tray](demo-stream-teaser.mp4)

*15s teaser (160KB). Full recording: [demo-stream.mp4](demo-stream.mp4) · [demo-stream.webm](demo-stream.webm)*

Recorded live: the raw Jetstream stream pours in, typing a regex splits it
green/red on the fly, the meaning tab scores a 5/s sample with Laya on the
default 6-way topic question (~200 ms/post on CPU), and verdicts for the
collected option (technology) drip into the reading tray — collect threshold
pushed to 95% first, then relaxed to 80% live when the confident drip slows.
The capture choreography (CDP screencast of headless chromium) stays scratch;
only the outputs are committed, like llm-arena-pareto's demo capture.

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


