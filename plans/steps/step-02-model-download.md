# Step 02 — download the Laya model

phase: env · machine: laptop · depends: step-01

## Goal
Checkpoint + vendor inference code on disk at `models/laya`, verified by file inventory.

## Do
1. From repo root, venv active:
```bash
hf download convaiinnovations/laya --local-dir models/laya
```
2. Verify inventory:
```bash
ls -la models/laya && du -sh models/laya
```
Expected contents: `model.safetensors` (~804 MB), `encoder/config.json`, `tokenizer/tokenizer.json` + `tokenizer_config.json`, `rl_agent_api.py`, `rl_common.py`, `rl_agent_config.json`, plus sub-checkpoints `multilingual/` and `typed-decisions/` (harmless — we use the root). Total ≈ 2.3 GB.
3. Add `models/` to `.gitignore` if the file exists (the full `.gitignore` is written in Step 03; a one-line add now is fine).

## Files you may touch
- `models/laya/**` (download only)
- `.gitignore` (one line)

## Accept
```bash
ls models/laya/model.safetensors models/laya/rl_agent_api.py models/laya/rl_common.py models/laya/encoder/config.json models/laya/tokenizer/tokenizer.json
```
All five paths exist, no error.

## Do NOT
- Load or run the model yet (Step 04 does that).
- Modify, reformat, or "clean up" anything inside `models/laya/` — vendor files are read-only.
- Report success without running the Accept command.
