# Step 03 — package skeleton + config + .gitignore

phase: env · machine: laptop · depends: step-01

## Goal
The importable package exists and `config.py` prints its values. No logic yet.

## Do
1. Create `laya_sort/__init__.py` (empty file).
2. Create `laya_sort/config.py` with exactly this shape (no more, no less):
```python
import os

DEVICE = os.environ.get("LAYA_DEVICE", "cpu")          # "cpu" | "cuda"
MODEL_DIR = os.environ.get("LAYA_MODEL_DIR", "models/laya")
JETSTREAM_URL = os.environ.get("JETSTREAM_URL", "wss://jetstream2.us-west.bsky.network/subscribe")
WANTED_COLLECTIONS = ["app.bsky.feed.post"]
LOG_PATH = os.environ.get("LAYA_LOG", "data/decisions.jsonl")
CURSOR_PATH = os.environ.get("LAYA_CURSOR", "data/cursor.json")
QUEUE_MAX = int(os.environ.get("LAYA_QUEUE_MAX", "10000"))
PORT = int(os.environ.get("LAYA_PORT", "8000"))
MIN_TEXT_LEN = int(os.environ.get("LAYA_MIN_TEXT", "30"))
LANGS = {"en"}   # languages kept by the pre-filter (Step 09)
```
3. Create directories: `data/`, `dashboard/`, `scripts/`, `fixtures/`.
4. Create `.gitignore` at repo root with exactly:
```
.venv/
models/
data/
__pycache__/
*.pyc
```

## Files
- create `laya_sort/__init__.py`, `laya_sort/config.py`, `.gitignore`
- create empty dirs `data/`, `dashboard/`, `scripts/`, `fixtures/`

## Accept
```bash
cd ~/Documents/laya-sort && python -c "from laya_sort import config; print(config.DEVICE, config.LOG_PATH, config.QUEUE_MAX)"
```
Prints `cpu data/decisions.jsonl 10000`. (Import works because cwd is on `sys.path` — that is the contract; there is no `pip install -e .`.)

## Do NOT
- Add extra config keys "for later" — keys appear when a step needs them.
- Create a `pyproject.toml`/`setup.py` — cwd-import is the deployment model.
- Put anything inside `data/` yet.
