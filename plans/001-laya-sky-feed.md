# Plan 001 — Laya Sky Feed (Bluesky feed generator, RTX 5090 target)

Status: **planned, not started** — 22 atomic steps in `plans/steps/`. Steps 01–15 laptop (CPU), 16–18 desktop (5090), 19–21 laptop, 22 gated go-live.

## 0. Objective

Build a Bluesky feed generator ("Laya Sky Feed") that:

1. Ingests the firehose via Jetstream (WebSocket, `app.bsky.feed.post` events).
2. Scores each post with the Laya RL agent **in-process** (fp16 autocast on CUDA), using the root `typed-decisions` checkpoint.
3. Appends every post + decision to an append-only JSONL log — the source of truth.
4. Shows the pipeline live in a single-file HTML/JS dashboard (SSE, localhost-only).
5. Later, gated: serves the ATProto feed-generator XRPC endpoints (`describeFeedGenerator`, `getFeedSkeleton`, `getServiceAuth`) on top of a derived SQLite ranking index.

Target demo: the pipeline running live on the 5090 box, visible in a browser, with every decision replayable offline from the log.

### Out of scope (MVP)

- Multilingual routing (the `multilingual/` checkpoint + Router mode). English-only feed.
- The Jev-compatible HTTP inference server — see decision D1.
- Rescoring, engagement signals, per-user customization, moderation plumbing.
- A ncurses/TUI frontend — rejected, see decision D8; the terminal view is `tail -f` on the log, for free.
- Publishing the feed record / going live (Step 7 is gated on separate approval).

## 1. Environments — laptop first, 5090 box for GPU only

Same code on both machines; the device is a config value, not a code path. Only the torch install line differs.

### Laptop (default dev box — plain Linux, CPU)

```bash
cd laya-sort
python3 -m venv .venv && source .venv/bin/activate
pip install torch transformers safetensors numpy huggingface_hub websockets   # CPU wheels
hf download convaiinnovations/laya --local-dir models/laya
LAYA_DEVICE=cpu python scripts/smoke_test.py
```

### Desktop (WSL2 Ubuntu on Windows 11, RTX 5090 — Blackwell, sm_120, 32GB)

- `nvidia-smi` works inside WSL (Windows NVIDIA driver with WSL CUDA support, driver ≥ 570). No Linux-side driver, no system CUDA toolkit — the pip wheels bundle their own runtime.
- **PyTorch ≥ 2.7 with cu128 wheels is required** for sm_120. Older cu126/earlier wheels lack Blackwell kernels → "no kernel image is available" errors.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install transformers safetensors numpy huggingface_hub websockets
hf download convaiinnovations/laya --local-dir models/laya
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Verify: output is `True NVIDIA GeForce RTX 5090`.

Model weights are 2.3GB total; the feed only needs `model.safetensors` (804M) + `encoder/` + `tokenizer/` + `rl_agent_config.json` + `rl_agent_api.py` + `rl_common.py` (~1.6GB). Download per machine, or copy the folder from the laptop (it already lives at `~/Documents/models/convaiinnovations/laya` there).

`requirements.txt` pins everything except the torch line — that stays per-machine in this README (CPU wheels vs cu128 index), because it's the one dependency that differs.

## 2. Architecture

### How the feed actually arrives

Not batches — an ordered stream of one event per message. The raw firehose emits opaque CAR blobs; we never touch it. **Jetstream** (official Bluesky-side proxy) re-emits it as plain JSON, one event per message, with a monotonic `seq` and a `?cursor=` resume parameter. We consume `wss://jetstream2.us-west.bsky.network/subscribe?wantedCollections=app.bsky.feed.post` — server-side filtering cuts traffic by orders of magnitude.

### Three pieces, one shared scoring function

```
[1] laya core (pure function + CLI)          # testable offline, no server
      score(post) -> {verdict, probabilities, confidence}
      doors: library import | python -m laya_sort.cli score post.json | daemon
[2] laya-daemon (the only long-running process)
      Jetstream WS -> bounded queue -> score() -> append data/decisions.jsonl
      FastAPI: GET /stream (SSE tail of the log) + static dashboard/index.html
[3] dashboard (single index.html, vanilla JS, no build step)
      EventSource('/stream') -> live feed of posts + verdicts
```

- The CLI never runs as a subprocess per post — torch would reload every time. The daemon imports the same scoring function; the CLI is its face for tests and offline A/B.
- `data/decisions.jsonl` is the source of truth. SQLite is a **derived** ranking index for skeleton queries, rebuildable from the log.
- The terminal view of the pipeline is free: `tail -f data/decisions.jsonl`.

Repo layout (flat, no speculative abstraction):

```
laya-sort/
  README.md               # runbook: two terminals (written in Step 13)
  plans/001-laya-sky-feed.md
  plans/steps/            # step-01 … step-22, one self-contained task per file
  laya_sort/              # package at repo root — no src/, no pip install needed
    config.py      # env-based: LAYA_DEVICE (cpu|cuda), LAYA_MODEL_DIR, thresholds, retention days
    questions.py   # the question set given to Laya (versioned: QUESTION_SET_V1)
    laya.py        # scoring function (pure): post dict -> verdict dict
    cli.py         # argparse: score a posts file / build-index / top
    jetstream.py   # WS consumer + bounded queue + cursor resume
    daemon.py      # consumer loop + FastAPI: SSE tail, /history, static dashboard
    store.py       # derived SQLite ranking index (rebuilt from the log)
    server.py      # XRPC endpoints + service auth (later phase)
  dashboard/
    index.html     # single file, vanilla JS + EventSource
  scripts/
    smoke_test.py  # load model, score 3 fixed posts, print answers + device line
    jetstream_probe.py  # connect, print first 10 raw events, list observed fields
    bench.py       # ≥5 samples, medians, GPU vs CPU baseline
    replay.py      # re-score a saved log, diff verdicts between rule versions
  fixtures/
    posts_v1.json  # 3 committed sample posts (created in Step 05)
  models/          # gitignored
  data/            # gitignored: decisions.jsonl, cursor.json, feed.sqlite
```

## 3. Decisions — defaults picked, you retain final say (veto any)

| # | Decision | Default | Consequences |
|---|---|---|---|
| D1 | Serving mode | **In-process RLAgent** in the feed service | + no hop, no second process, single dep set. − model memory lives in the feed process. A Jev HTTP server adds a process + hop for zero benefit with one consumer. |
| D2 | Language | **English-only**, root `typed-decisions` checkpoint | + no Router, one model, fastest path. − excludes non-en posts (acceptable for MVP). |
| D3 | Precision | fp16 autocast, exactly as shipped in `rl_agent_api.py` | matches vendor code, no forking the model repo; 5090 handles fp16 natively. |
| D4 | Scoring cadence | score on arrival, one stream worker, bounded queue (drop when > 10k) | + simple. − peak firehose (~30–50 posts/s) can exceed the single-forward scoring ceiling (GPU ~30/s; laptop CPU far lower) → backlog drains over time; pre-filter mitigates. Measured in Step 2, not assumed. |
| D5 | Ranking | calibrated score DESC, `createdAt` tiebreak, no recency decay | + deterministic, simple pagination. − old high scorers can sit on top; add decay later only if the feel is wrong. |
| D6 | Ranking index | SQLite single file, derived from the log (see D10) | + zero-ops, fast keyset pagination for skeleton queries. − single writer process only; index is disposable, the log is not. |
| D7 | Go-live transport | cloudflared tunnel (or ngrok static domain) serving both the DID doc and XRPC from one host | + fastest live path. − tunnel dependency; swappable for a VPS later without code changes. |
| D8 | Frontend | **Single-file HTML/JS dashboard** (vanilla JS, no build step) | + your home turf, live view with zero tooling. ncurses rejected: JS TUI libs are half-abandoned and terminal graphs are miserable; the terminal view is `tail -f` on the log anyway. |
| D9 | Dashboard transport | **SSE** (`GET /stream`), not WebSocket | + one-way push is exactly the use case; the browser auto-reconnects; ~20 lines server-side. WS needs hand-rolled reconnect for no benefit. |
| D10 | Persistence split | `decisions.jsonl` = source of truth; SQLite = derived index | + log is replayable and A/B-able, survives UI crashes; ranking index rebuildable. − two stores; a rebuild command must exist. |
| D11 | Run mode | No service manager: a README runbook — two terminals, two commands (start the daemon; `tail -f` the log) | + zero magic, matches how you actually work; the README is the only ops doc. − manual restart after reboot; add a systemd unit later only if that gets annoying. |

## 4. Execution protocol — one atomic step at a time

Each step lives in its own file under `plans/steps/` and is a **complete, self-contained task definition**. How to run with any executor model (cheap is fine):

1. Fresh session, hand it exactly one file: `@plans/steps/step-07.md` + one line: "Execute this step."
2. The step file is the whole spec. If something it needs is missing or ambiguous, the executor must **stop and report** — never improvise scope, never touch files outside its file list.
3. Every step ends with an **Accept** section: a command with observable output, or a precise manual checklist. Acceptance not passing → the step is not done; stop there and report.
4. The executor never commits. You review the diff, stage, commit.
5. Steps are sequential; each file names its dependency. Do not skip ahead — a failed earlier step invalidates everything after it.

| file | phase | machine | delivers |
|---|---|---|---|
| step-01 | env | laptop | venv + all deps (CPU torch) |
| step-02 | env | laptop | model downloaded to `models/laya` |
| step-03 | env | laptop | package skeleton + `config.py` + `.gitignore` |
| step-04 | env | laptop | `smoke_test.py`: load agent, score 3 posts, print device |
| step-05 | core | laptop | `questions.py` v1 + `laya.score()` + fixture + determinism check |
| step-06 | core | laptop | CLI: score a posts file → JSONL verdicts |
| step-07 | core | laptop | `replay.py`: offline re-scoring, determinism proof |
| step-08 | net | laptop | Jetstream probe: 10 raw events + observed field list |
| step-09 | net | laptop | post parsing + en/length/reply filters + counters |
| step-10 | net | laptop | bounded queue + scoring consumer + status lines |
| step-11 | net | laptop | cursor resume + reconnect + dedupe |
| step-12 | net | laptop | 60s live acceptance of the whole pipeline |
| step-13 | ui | laptop | daemon: static + SSE `/stream` + `/history` + README runbook |
| step-14 | ui | laptop | `dashboard/index.html` live view |
| step-15 | ui | laptop | resilience: kill/restart mid-stream, nothing lost |
| step-16 | gpu | desktop | CUDA env + model on the 5090 box |
| step-17 | gpu | desktop | same smoke test with `LAYA_DEVICE=cuda` |
| step-18 | gpu | desktop | bench: GPU fp16 vs CPU medians |
| step-19 | feed | laptop | SQLite ranking index rebuilt from the log |
| step-20 | feed | laptop | XRPC `describeFeedGenerator` + `getFeedSkeleton` |
| step-21 | feed | laptop | service auth verification |
| step-22 | feed | gated | publish feed record + go live (you present, account needed) |

## 5. Unknowns — resolved inside the step that discovers them, never assumed

- Exact `state` schema `system_one` expects for posts → Step 04 prints the signature + docstring first, then adapts.
- `transformers` version compatibility with the encoder arch → Step 04 smoke; pin in `requirements.txt` only after it passes.
- Real firehose rate vs the CPU scoring ceiling → measured in Steps 09–12 (laptop CPU is the worst case).
- Jetstream message fields + replay-on-reconnect semantics → Step 08 prints the actual fields (`seq`, `time_us`, …); Step 11 implements resume + dedupe against them.
- SSE across WSL2 localhost to a Windows browser → laptop covers plain localhost in Steps 13–15; the desktop live run in Steps 16–18 re-checks the WSL boundary.

## 6. Measurement rules

- Wall-clock latency and queue depth only; no proxy metrics.
- ≥5 samples, report median + p90.
- GPU vs CPU on the same box, same posts — fair baseline.
- No "fast demo" claim before Step 2 medians exist.
