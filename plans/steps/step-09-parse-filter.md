# Step 09 — parse posts + pre-filter + honest counters

phase: net · machine: laptop · depends: step-08

## Goal
Raw Jetstream messages → clean post dicts, filtered, with every drop counted. No scoring yet.

## Do
1. In `laya_sort/jetstream.py` implement:
   - `async def consume(handler, seconds=None)` — connects with the `wantedCollections` query param from config, iterates messages, and per message:
     - keep only `commit.collection == "app.bsky.feed.post"` and create-type operations (belt-and-braces: the URL already filters).
     - extract: `did` (author), `commit.rkey` → uri `at://<did>/app.bsky.feed.post/<rkey>`, `commit.cid`, `record.text`, `record.langs`, `record.created_at` (fall back to the message time field from Step 08 if absent), `record.reply` (None → not a reply).
     - post dict shape: `{"uri","cid","text","langs","author","created_at","reply"}`.
   - keep-rule (from `config`): `set(langs) & config.LANGS != ∅`, `len(text) >= config.MIN_TEXT_LEN`, `record.reply is None`.
   - counters: `seen, kept, dropped_lang, dropped_short, dropped_reply, dropped_other` — every drop lands in exactly one bucket.
   - `counters_report()` → single summary line.
2. Create `scripts/run_reader.py`: runs `consume(counting_handler, seconds=60)` then prints the report.

## Files
- create `laya_sort/jetstream.py`, `scripts/run_reader.py`

## Accept
```bash
python scripts/run_reader.py
```
After 60s prints one line like `seen=1832 kept=412 dropped_lang=201 dropped_short=1187 dropped_reply=22 dropped_other=0` (numbers will differ; the shape is the contract): all six counters present, `kept > 0`, buckets sum to `seen`.

## Do NOT
- Score anything yet (Step 10 wires the consumer).
- Swallow parse errors — a malformed message increments `dropped_other` (with a one-line stderr note), it never crashes the loop.
