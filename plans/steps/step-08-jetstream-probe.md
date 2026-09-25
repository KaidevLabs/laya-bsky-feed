# Step 08 — Jetstream probe: raw events + field discovery

phase: net · machine: laptop · depends: step-01, step-03

## Goal
Prove the WebSocket connects and record the EXACT message fields — the ordering key (`seq`?) and time key (`time_us`?) that Step 11's cursor design depends on. Nothing is assumed.

## Do
1. Create `scripts/jetstream_probe.py`:
   - Sync `websockets` client is fine here (one-shot script).
   - URL: `config.JETSTREAM_URL + "?wantedCollections=" + ",".join(config.WANTED_COLLECTIONS)`.
   - Print the first 10 messages, each as `json.dumps(msg)[:300]`.
   - While receiving, collect the union of: top-level keys across messages, `commit` sub-keys, and the set of `commit.collection` values seen.
   - Write findings to `data/probe_fields.json`: `{"top_level_keys": [...], "commit_keys": [...], "collections": [...], "sample_message": <first full message>}`.
2. If the connection fails, print the exception verbatim and stop — network/VPN issue, report it, do not hack around it.

## Files
- create `scripts/jetstream_probe.py`

## Accept
```bash
timeout 60 python scripts/jetstream_probe.py
```
- 10 events printed; `data/probe_fields.json` exists and contains the key lists.
- Your report names the exact ordering and time fields observed (e.g. `seq`, `time_us`) and where the post text lives (`commit.record.text`?).

## Do NOT
- Keep the connection open indefinitely — exit after 10 messages.
- Parse deeper than top-level + `commit` (that is Step 09).
- Guess field names in the report — copy them from the output.
