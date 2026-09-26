# Execution log — 2026-09-25/26 orchestrator run

How this run worked: one fresh executor session per step, each given **only its own step
file** plus the accumulated deviations; the orchestrator reviewed diffs, re-verified
accepts where cheap, and committed (executors never commit). This file is the durable
record for the review pass.

## Run context

- Everything ran on the **laptop** (Docker container, Ryzen 9 7940HS,
  16 cores, CPU only). The 5090 desktop has no reachable route from this container.
- **User decision:** steps 16–18 run as CPU stand-ins here; the real 5090 run (and step
  16's `True RTX 5090` / step 18's ≤ 50 ms gate) stays open.
- **User constraint (late, now enforced):** all work inside the repo; scratch only in
  `/tmp/opencode`. One earlier command briefly carried a wrong workdir; it was aborted
  before executing (no effect).
- Live firehose accepts were run for real (Jetstream `jetstream2.us-west`).

## Steps

| step | status | commit | accepted | deviations (executor-reported) |
|---|---|---|---|---|
| 01 venv+deps | done | — (venv only, self-ignored) | imports print ok; cuda False | `huggingface_hub` downgraded 2.0.0→1.33.0 (forced by transformers 5.17.0 pin); torch 2.14.0+cu130 PyPI wheel (CPU-verified); direct `.venv/bin` binaries |
| 02 model | done | — (models/ gitignored) | 5-file inventory | none (`hf download` per spec, no local copy) |
| 03 skeleton+config | done | `1069766` | config prints cpu / data/decisions.jsonl / 10000 | none |
| 04 smoke test | done | `eb30e0a` | deterministic ×2, exit 0, `STATE_SCHEMA=` printed | venv python for accept; device line printed twice (spec ordering tension); STATE_SCHEMA printed unconditionally; repo root on sys.path |
| 05 scoring core | done | `08df39e` | `CHECK SCORE PASS`, byte-identical across runs AND processes | smoke_test.py absent at start (see PD1) → re-derived API from vendor source, cross-checked vs committed smoke test; absolute vendor path in laya.py; billing verdict B (not plan's "likely A"; matches step-04 record) |
| 06 CLI | done | `29fe383` | 3 verdicts, byte-identical to check_score, exit 0 | parser renamed `read_posts` by step-07's cross-edit (confirmed, not fought) |
| 07 replay | done | `5acf0c5` | two runs byte-identical (sha256 match) | renamed step-06's parser to the spec'd name (cross-executor edit); venv python |
| 08 Jetstream probe | done | `0aa867f` | 10 raw events + field list | explicit 30s/45s timeouts; **key fact: no `seq` on the wire** — `time_us` (µs-epoch, strictly increasing) is the only ordering key |
| 09 parse+filter | done | `e229244` | live 60s: seen=2495 kept=534, buckets sum to seen | wire `createdAt` camelCase; created_at fallback = raw time_us; identity/account kinds + deletes → `dropped_other`; +30s connect timeout |
| 10 queue+consumer | done | `e229244` | live 60s: scored=530==kept, log lines==scored, backpressure proven (QUEUE_MAX=3 → 95 drops, no block) | 3 shared counters added (`dropped_backpressure`, `scored`, `score_errors`); latency rounded 2dp; agent preloaded on main thread |
| 11 cursor+resume | done | `e229244` | two 45s runs → `NO DUPES 3309`; inclusive-resume deduped live (`skipped_dup=1`); ~12.9k catch-up in 10s | seq is **self-maintained** (wire has none); dedupe key `time_us`; in-process reconnect resumes at read head; per-pid cursor tmp (fixes a live cross-writer crash); log lines carry `time_us`; consume() also resumes from cursor |
| 12 GATE | **re-adjudicated** | — (no files) | executor's final report never arrived; orchestrator re-ran the essentials on final code (see below) | see "Gate adjudication" |
| 13 daemon SSE | done | `fe8b767` | /history OK; /stream live (31 SSE lines in 10s == exact log growth, consumer kept scoring while attached; ping ~15s); clean SIGINT | `GET /` 500 pending step-14 file (file-split design, not a bug); model load 15–35s vs spec'd `sleep 20`; daemon left running for step 14 (stopped since); starlette `Content-Disposition` quirk did **not** materialize |
| 14 dashboard | done | `b09db1b` | page's own script executed vs live daemon in a text-only DOM harness: 20 history cards @104ms, SSE live cards, cap 50, 3 spot-check cards exact-match log lines | "open in a browser" done text-only (vision unavailable on this server); card text falls back to AT URI (log has no text field); first executor session died on provider error "Vision is disabled for this server", fresh session finished |

## Gate adjudication (step 12)

- Executor's evidence before its report was lost: 60s read window `seen=39839 kept=8251`,
  `dropped_backpressure=0`; drain proceeded at ~250 ms/post; the process then crashed at
  final cursor persist — **cause**: two pipelines (step-12 run + step-13 daemon) writing
  `cursor.json` via the same literal `.tmp` path. Step 11's per-pid tmp fix is in the code
  the running processes predate.
- Orchestrator re-verification on the **final** code: fresh 12s live run — 131 log lines
  appended, region has seq strictly increasing / uris unique / `time_us` non-decreasing,
  `cursor.json` == last line, zero errors, clean exit semantics; py_compile clean for
  jetstream/daemon/laya/cli.
- **Open item — replay cross-check:** confirmed blocked by a **spec gap** (not a code
  bug): `laya.score()` requires `post["text"]` but decision-log lines carry
  `{uri, author, created_at, verdict, probabilities, confidence, question_set,
  latency_ms, scored_at, seq, time_us}` — no `text` (`KeyError: 'text'` proven live).
  Decision needed: (a) append `text` to log lines, or (b) have live runs also capture a
  posts side-file the replay can consume. The determinism property itself is proven
  (step 07 byte-identical).

## Process deviations (orchestrator scheduling — not plan defects)

- PD1–PD8: steps 05–14 were launched before the previous step's report landed (early
  launches). Consequences: step-05 stopped and re-derived the API (safe path, no rework);
  step-07 renamed step-06's parser mid-flight (regression-verified); steps 09→11 extended
  `jetstream.py` in place (final state re-verified, committed once with attribution);
  step-12 + step-13 ran two pipelines concurrently → the cursor tmp race above and a
  128-pair `(seq,uri)` duplicate region in the disposable dev log.
- Step-14's first executor died on a provider error (vision disabled) mid-accept; a fresh
  session completed the accept text-only.

## Open items for the review pass

1. Re-run the full step-12 gate (60s window + full drain) on final code; decide the
   replay-from-log gap (add `text` to log lines vs posts side-capture).
2. `data/decisions.jsonl` currently mixes writers: a 128-dup-pair region (lines ~5944–6199
   of that era) from the concurrent runs. It's gitignored dev data — wipe or dedupe by uri.
3. Firehose rate varies wildly by window (raw 41 → 664 msg/s; kept 9 → 137/s). CPU scores
   ~4 posts/s, so peak-window backpressure drops are **by design** (D4); the queue drains
   over minutes. GPU (~30/s) still won't match the busiest windows.
4. Steps 15–22 not started. 16–18 as CPU stand-ins until the 5090 desktop is reachable;
   step 16 `True RTX 5090` and step 18 ≤ 50 ms gate remain open.
5. Human browser pass on `http://127.0.0.1:8000` (the dashboard was verified text-only;
   vision was unavailable). Daemon is stopped — restart per the README runbook.
6. Steps 06/07's reserved `build-index`/`top` stubs await step 19.
7. Post-plan addition (user-requested, committed outside the 22-step scope):
   `dashboard/stream.html` — standalone Jetstream playground with two modes:
   regex (green/red split, live re-classification) and meaning (arbitrary
   one-question verdicts via `scripts/meaning_server.py`, sample-then-score,
   amber-queued → option-colored cards, live tally, backfill). The meaning
   server reuses `laya_sort.laya.get_agent()` — same door, no pipeline conflict;
   measured ~200ms/post on CPU, one forward pass per post with all options.

## Verified facts worth keeping (discovered, not assumed)

- **Jetstream wire:** top-level `commit, did, kind, time_us` — **no `seq`**; `commit` =
  `cid, collection, operation, record, rev, rkey`; post text at `commit.record.text`;
  record has `createdAt` (ISO-8601), `langs`, `reply`; `wantedCollections` still passes
  `identity`/`account` kinds and deletes (filtered client-side).
- **Cursor semantics (verified against the real server):** `?cursor=<time_us>` accepted;
  resume is **inclusive** (the cursor message is redelivered exactly once — dedupe
  mandatory); catch-up replay from cursor to live edge; retention ≥ 30 min.
- **Vendor API (`models/laya`):** `RLAgent(model_dir, device)`; `system_one(state,
  questions)` — state str or JSON-serializable (json.dumps'd); one call = one forward pass
  for all questions; `choice` answers carry `probabilities`+`confidence`, `noul` carries
  neither; temperatures bucket-scaled per (qtype, option-count); `act_probability` always
  1.0 (vendor issue #185); `max_len=512`, `head_max_len=192`; base EN checkpoint is
  near-chance on ad-hoc zero-shot questions (expected pre-fine-tuning).
- **Scoring (CPU, fixture v1):** all 3 posts → verdict B, confidence 0.004–0.047;
  byte-identical across runs and processes.

## Commit map

`1069766` step 03 · `eb30e0a` step 04 · `08df39e` step 05 · `29fe383` step 06 ·
`5acf0c5` step 07 · `0aa867f` step 08 · `e229244` steps 09–11 · `fe8b767` step 13 ·
`b09db1b` step 14 · docs commit: plan status + this file.