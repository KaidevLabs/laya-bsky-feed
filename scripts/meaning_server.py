"""Meaning server: arbitrary Laya questions over HTTP for dashboard/stream.html.

The playground page connects to Jetstream directly in the browser; this server
is only the scoring brain: POST /ask with a question (instructions + short
option labels) and 1..20 texts, get one verdict per text. The vendor agent
runs exactly one forward pass per text; all options ride the same pass.

Run:  python scripts/meaning_server.py          (port via LAYA_MEANING_PORT, default 8100)
Health: curl http://127.0.0.1:8100/health       -> {"device": "cpu", "loaded": true}
"""
import contextlib
import io
import os
import sys
import threading
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from laya_sort import config, laya  # noqa: E402

MAX_TEXTS = 20
MAX_OPTIONS = 8

app = FastAPI(title="laya meaning server")
# The page may be opened from file:// (Origin "null") or any static port.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

_load_lock = threading.Lock()
_pass_lock = threading.Lock()   # one forward pass at a time (torch, no concurrency)
_loaded = False


def _ensure_agent():
    """Load the vendor agent exactly once (thread-safe; get_agent prints a line)."""
    global _loaded
    with _load_lock:
        if not _loaded:
            t0 = time.time()
            load_log = io.StringIO()
            with contextlib.redirect_stdout(load_log):
                laya.get_agent()
            _loaded = True
            print("[meaning] agent ready in %.1fs %s"
                  % (time.time() - t0, load_log.getvalue().strip()), flush=True)


class Question(BaseModel):
    text: str = Field(min_length=1, description="question instructions")
    options: list = Field(min_length=2, max_length=MAX_OPTIONS,
                          description="short option labels; index 0 -> option A, ...")


class AskBody(BaseModel):
    question: Question
    texts: list = Field(min_length=1, max_length=MAX_TEXTS)


@app.get("/health")
def health():
    return {"device": config.DEVICE, "model_dir": config.MODEL_DIR, "loaded": _loaded}


@app.post("/ask")
def ask(body: AskBody):
    _ensure_agent()
    criteria = {chr(ord("A") + i): str(opt)[:80] for i, opt in enumerate(body.question.options[:MAX_OPTIONS])}
    question = {"q": {"type": "choice", "instructions": body.question.text, "criteria": criteria}}
    results = []
    with _pass_lock:
        for text in body.texts[:MAX_TEXTS]:
            t0 = time.time()
            try:
                out = laya.get_agent().system_one(str(text), question)
                ans = out["answers"]["q"]
                results.append({
                    "verdict": ans["choice"],
                    "option": criteria.get(ans["choice"], "?"),
                    "probabilities": ans.get("probabilities", {}),
                    "confidence": ans.get("confidence", 0.0),
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                    "error": "",
                })
            except Exception as e:  # e.g. option label overflows the option head budget
                results.append({
                    "verdict": "", "option": "", "probabilities": {}, "confidence": 0.0,
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                    "error": "%s: %s" % (type(e).__name__, e),
                })
    return {"device": config.DEVICE, "results": results}


@app.on_event("startup")
def prewarm():
    """Load the model in the background so the first /ask is fast."""
    threading.Thread(target=_ensure_agent, daemon=True).start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1",
                port=int(os.environ.get("LAYA_MEANING_PORT", "8100")))
