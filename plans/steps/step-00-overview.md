# Step 00 — Overview (read this first)

phase: meta · machine: n/a · depends: nothing

## What this project is

**Laya Sky Feed** — a Bluesky feed pipeline that runs entirely on your own hardware:

```
Jetstream WebSocket (official JSON firehose proxy, filtered to posts)
  → pre-filter (English, min length, not a reply)
  → Laya decision engine (one forward pass per post, calibrated verdict)
  → append-only JSONL log (the source of truth)
  → single-file HTML/JS dashboard over SSE (localhost)
  → later, gated: ATProto feed generator (SQLite index + XRPC endpoints)
```

Master plan: `plans/001-laya-sky-feed.md` (architecture, decisions D1–D11, environments, measurement rules). The steps below are the executable pieces.

## How to execute a step

1. Open a **fresh session** with the executor model (cheap is fine) and hand it exactly one file: `@plans/steps/step-07.md` plus one line: "Execute this step."
2. The step file is the whole spec. If anything it needs is missing or ambiguous, the executor must **stop and report** — never improvise, never touch files outside its file list.
3. Every step ends with an **Accept** section: a command with observable output. Acceptance not passing → the step is not done; stop there.
4. The executor **never commits**. You review the diff, stage, and commit (conventional message + why in the body).
5. Steps are sequential — each file names its dependency. A failed earlier step invalidates everything after it.

## Machines

| machine | role | steps |
|---|---|---|
| laptop (plain Linux, CPU) | default dev box — everything is built and run here first | 01–15, 19–21 |
| desktop (WSL2 + RTX 5090) | only the GPU-coupled work, then hosts the live demo | 16–18, 22 |

## All steps

| # | path | phase | machine | delivers |
|---|---|---|---|---|
| 01 | `plans/steps/step-01-venv-cpu.md` | env | laptop | venv + all deps (CPU torch); accept: imports print ok |
| 02 | `plans/steps/step-02-model-download.md` | env | laptop | model at `models/laya`; accept: 5-file inventory |
| 03 | `plans/steps/step-03-skeleton-config.md` | env | laptop | package skeleton + `config.py` + `.gitignore` |
| 04 | `plans/steps/step-04-smoke-test.md` | env | laptop | agent loads on CPU, 3 posts scored, API discovered (`STATE_SCHEMA=`) |
| 05 | `plans/steps/step-05-scoring-core.md` | core | laptop | `questions.py` v1 + pure `score()` + fixture + determinism check |
| 06 | `plans/steps/step-06-cli.md` | core | laptop | CLI: score a posts file → JSONL verdicts |
| 07 | `plans/steps/step-07-replay.md` | core | laptop | offline re-scoring; accept: two runs byte-identical |
| 08 | `plans/steps/step-08-jetstream-probe.md` | net | laptop | 10 raw events printed + real field names (`seq`, `time_us`) |
| 09 | `plans/steps/step-09-parse-filter.md` | net | laptop | post parsing + en/length/reply filters + honest counters |
| 10 | `plans/steps/step-10-queue-consumer.md` | net | laptop | bounded queue + scoring consumer (`asyncio.to_thread`) + status lines |
| 11 | `plans/steps/step-11-cursor-resume.md` | net | laptop | cursor resume + reconnect + no-duplicate proof |
| 12 | `plans/steps/step-12-live-acceptance.md` | net | laptop | **GATE**: 60s live run + replay cross-check — pipeline core done |
| 13 | `plans/steps/step-13-daemon-sse.md` | ui | laptop | daemon: SSE `/stream` + `/history` + README runbook |
| 14 | `plans/steps/step-14-dashboard-html.md` | ui | laptop | single-file dashboard, live cards |
| 15 | `plans/steps/step-15-resilience.md` | ui | laptop | kill/restart mid-stream — nothing lost |
| 16 | `plans/steps/step-16-desktop-env.md` | gpu | desktop | CUDA env + model; accept: `True RTX 5090` |
| 17 | `plans/steps/step-17-cuda-smoke.md` | gpu | desktop | same smoke test with `LAYA_DEVICE=cuda` |
| 18 | `plans/steps/step-18-bench.md` | gpu | desktop | **GATE**: GPU fp16 vs CPU medians; GPU p50 ≤ 50 ms/post |
| 19 | `plans/steps/step-19-sqlite-index.md` | feed | laptop | SQLite ranking index, rebuilt from the log |
| 20 | `plans/steps/step-20-xrpc-endpoints.md` | feed | laptop | `describeFeedGenerator` + `getFeedSkeleton` |
| 21 | `plans/steps/step-21-service-auth.md` | feed | laptop | verify AppView-signed requests; unsigned → 401 |
| 22 | `plans/steps/step-22-golive.md` | feed | **gated** | publish feed + go live — you in the loop, account steps are yours |

## The three gates

- **Step 12** — pipeline core acceptance. UI work does not start until every check passes.
- **Step 18** — GPU bench ≤ 50 ms/post. If it fails, the "fast demo" claim dies honestly; no tuning, report and stop.
- **Step 22** — go-live. Touches your Bluesky account and goes public; you run the account/tunnel parts.

## Two honest caveats

- Laptop CPU scoring is slow (~hundreds of ms/post). The pipeline is built and proven there; the *fast* demo only exists after Step 18.
- Steps 04 and 08 are **discovery** steps: they print what the vendor API and Jetstream actually expect. Later steps build on those printed facts, not on assumptions — if the printed facts differ from any example in a step file, the printed facts win.
