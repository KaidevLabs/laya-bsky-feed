"""Laya Sky Feed daemon: the single long-running process (Step 13).

Scores the live Jetstream stream AND serves the decision log to
viewers. The pipeline is the exact callable the CLI runs
(laya_sort.jetstream.main -> asyncio.run(jetstream.run(...))); the
FastAPI lifespan starts it as a task on the server's event loop with
seconds=None, so it runs until stopped. Scoring itself stays on
asyncio.to_thread inside jetstream (Step 10 pattern) — the event loop
only ever handles HTTP.

HTTP surface (localhost-only, D9/D11):
  GET /        -> FileResponse("dashboard/index.html")
  GET /stream  -> SSE: tails config.LOG_PATH from the connect-time
                 end-of-file; polls for new bytes every 250 ms; one
                 "data: <line>\n\n" per complete new line; a
                 ": ping\n\n" comment every 15 s to keep intermediaries
                 alive. The tail is maintained from a byte offset (plus
                 the partial line in flight), so each poll reads only
                 what was appended since the last poll — the log is
                 never re-read whole.
  GET /history -> {"items": [...]}: the last n complete log lines as
                 JSON objects, n clamped to 1..100 (default 20).

Run from the repo root:  python -m laya_sort.daemon
"""
import asyncio
import contextlib
import io
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from laya_sort import config, jetstream, laya

POLL_SECONDS = 0.25   # /stream: poll interval for new log bytes
PING_SECONDS = 15.0   # /stream: SSE keep-alive comment interval
HISTORY_DEFAULT = 20  # /history: default n
HISTORY_MAX = 100     # /history: clamp bound


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the pipeline on server startup; stop it on shutdown.

    Same code path as `python -m laya_sort.jetstream` (which runs
    asyncio.run(jetstream.run(seconds=...))): the same callable, here a
    task on the uvicorn loop, without --seconds — runs until stopped.
    """
    consumer_task = asyncio.create_task(jetstream.run(seconds=None))
    try:
        yield
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        except Exception as e:  # a failed pipeline never exits silently
            print("consumer task failed: %s: %s" % (type(e).__name__, e),
                  file=sys.stderr)


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse("dashboard/index.html")


async def _sse_tap():
    """Async generator: tail config.LOG_PATH from the connect-time EOF.

    Polls for new bytes every POLL_SECONDS and yields one
    "data: <line>\n\n" per complete new line, plus a ": ping\n\n"
    comment every PING_SECONDS. Tracks a byte offset (and the partial
    line in flight) so each poll reads only what was appended since
    the last poll. If the log is missing, it is waited for; if it is
    truncated or replaced, the tail restarts from the top.
    """
    f = None
    offset = 0
    partial = b""
    last_ping = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            if now - last_ping >= PING_SECONDS:
                last_ping = now
                yield ": ping\n\n"
            if f is None:
                try:
                    f = open(config.LOG_PATH, "rb")
                except OSError:
                    await asyncio.sleep(POLL_SECONDS)
                    continue
                f.seek(0, os.SEEK_END)
                offset = f.tell()
            size = f.seek(0, os.SEEK_END)
            if size < offset:
                # The log was truncated or replaced: tail from the top.
                offset = 0
                partial = b""
            f.seek(offset)
            data = f.read()
            if data:
                offset += len(data)
                *complete, partial = (partial + data).split(b"\n")
                for line in complete:
                    if line:
                        yield "data: %s\n\n" % line.decode("utf-8", "replace")
            await asyncio.sleep(POLL_SECONDS)
    finally:
        if f is not None:
            f.close()


@app.get("/stream")
async def stream():
    """SSE: the live tail of the decision log (see _sse_tap)."""
    return StreamingResponse(_sse_tap(), media_type="text/event-stream")


@app.get("/history")
async def history(n: int = HISTORY_DEFAULT):
    """The last n complete log lines, as JSON objects (n clamped to 1..100)."""
    n = max(1, min(HISTORY_MAX, n))
    try:
        data = Path(config.LOG_PATH).read_bytes()
    except OSError:
        return {"items": []}
    lines = data.split(b"\n")[:-1]  # drop b"" or a partial trailing line
    items = []
    for line in lines[-n:]:
        try:
            items.append(json.loads(line.decode("utf-8")))
        except (UnicodeDecodeError, ValueError):
            items.append(line.decode("utf-8", "replace"))
    return {"items": items}


def main():
    # Load the RL agent up front, on the main thread, so the worker
    # threads never race on the lazy init (same treatment as
    # jetstream.main: the device line goes to stderr).
    load_log = io.StringIO()
    with contextlib.redirect_stdout(load_log):
        laya.get_agent()
    if load_log.getvalue():
        sys.stderr.write(load_log.getvalue())
        sys.stderr.flush()
    uvicorn.run(app, host="127.0.0.1", port=config.PORT)


if __name__ == "__main__":
    sys.exit(main())
