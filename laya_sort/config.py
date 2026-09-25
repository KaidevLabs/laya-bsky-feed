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
