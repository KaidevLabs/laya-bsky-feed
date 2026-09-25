# Step 04 — smoke test on CPU: load agent, score 3 fixed posts, discover the API

phase: env · machine: laptop · depends: step-02, step-03

## Goal
Proof that the vendor inference code loads and answers on CPU — and a printed record of the exact `system_one` API (signature, docstring, expected state type). Step 05 depends on that record.

## Do
1. Create `scripts/smoke_test.py`:
   - Insert the vendor dir on the path — vendor code stays untouched:
     `sys.path.insert(0, "models/laya")` then `import rl_agent_api`.
   - FIRST (before loading weights) print discovery info:
     - `inspect.signature(rl_agent_api.RLAgent.system_one)` and its docstring
     - from `models/laya/rl_agent_config.json`: `max_len`, `head_max_len`, `encoder`
   - Then: `agent = rl_agent_api.RLAgent(config.MODEL_DIR, device=config.DEVICE)`.
     The root `models/laya` is the English checkpoint. If the root load raises, retry with `models/laya/typed-decisions` and print which dir was used.
   - Three fixed posts as inline literals (do not read files):
     a) billing complaint: "Hi, we were billed twice for March, please refund the duplicate charge."
     b) chit-chat: "coffee was great today, might go again tomorrow"
     c) Spanish: "La aplicación se cierra cada vez que abro la configuración."
   - A throwaway `SMOKE_QUESTIONS` dict: one two-option `choice` (keys `"A"`/`"B"`, criteria: A = "a substantive post worth showing", B = "chit-chat or noise") and one `noul` — shapes exactly as used in the vendor README quickstart.
   - Call `agent.system_one(state, SMOKE_QUESTIONS)` per post; print each raw answers dict.
   - Final line: `device=<config.DEVICE> checkpoint=<dir used>`.
2. If `system_one` rejects the state (dict vs str): READ `models/laya/rl_agent_api.py` and `build_sequence` in `models/laya/rl_common.py`, find the expected state type, adapt, and print a line `STATE_SCHEMA=<what worked>` — verbatim, Step 05 depends on it.

## Files
- create `scripts/smoke_test.py`

## Accept
```bash
cd ~/Documents/laya-sort && LAYA_DEVICE=cpu python scripts/smoke_test.py
```
- Prints signature + docstring + config keys, then `device=cpu checkpoint=...`, then 3 answer blocks, each with per-option probabilities (sum ≈ 1.0) and a `confidence` key. Exit code 0.
- The `STATE_SCHEMA=` finding is included in your report.

## Do NOT
- Modify anything under `models/laya/`.
- Copy vendor code into `laya_sort/` — we import it in place.
- Declare done if any Accept line is missing; paste the full traceback and stop.
