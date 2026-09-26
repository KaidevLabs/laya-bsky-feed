"""Jetstream consumer: raw messages -> filtered posts -> bounded queue -> scoring (Steps 09/10).

Connects to the Jetstream WebSocket (config.JETSTREAM_URL, with the
wantedCollections query param from config.WANTED_COLLECTIONS), parses each
raw message into a post dict, applies the pre-filters (language, minimum
text length, not a reply) and pushes every kept post onto a bounded
asyncio.Queue (maxsize=config.QUEUE_MAX). A single consumer task pops
posts and scores them with laya.score() inside asyncio.to_thread (score
is blocking torch work and must NOT run on the event loop), so the WS
read loop never blocks on model inference. If the queue is full, the
incoming post is dropped and counted in dropped_backpressure — the reader
never awaits on a full queue and dropped events are never remembered.

Each scored post is appended to config.LOG_PATH as one JSON line: the
verdict dict (see laya.score) plus latency_ms (monotonic, receive ->
scored, in ms), a scored_at wall-clock timestamp (UTC) and the stream
position (seq, time_us). One status line goes to stderr every 10s; the
final report (all counters + latency median/p90) goes to stdout.

Run from the repo root:  python -m laya_sort.jetstream --seconds N

Wire facts (from the Step 08 probe, data/probe_fields.json):
  top level: did, time_us (microseconds), kind, commit
  commit:    rev, operation ("create"/...), collection, rkey, record, cid
  record:    app.bsky.feed.post record: text, langs, createdAt, reply, ...

Stream position / resume (Step 11, verified against the live server):
the wire carries NO seq field — time_us (strictly increasing int,
microsecond epoch) is the only ordering key. ?cursor=<time_us> resumes
the stream inclusively: the server redelivers the message AT the cursor
exactly once, then continues strictly after it, and catches up from an
old cursor to the live edge (retention observed >= 30 minutes). This
module therefore maintains its own monotonic stream index: every
non-duplicate received message is assigned the next seq (continuing
from the persisted cursor), and a message whose time_us is at or before
the resume point is a resume duplicate: skipped, counted in
skipped_dup (aggregate only — debug level, no per-skip line). Every
successful decision-log append atomically persists the position as
{"seq": <last seq>, "time_us": <last time_us>} to config.CURSOR_PATH
(write to a per-process tmp file <path>.tmp.<pid>, os.replace — the tmp
name is unique per process so concurrent persisters can't steal each
other's half-written file). The daemon reader reconnects after
backoff 1s -> 2s -> 4s -> ... capped at 30s; each (re)connect resumes
from the in-process read head once any message has been received
(posts read but not yet appended still sit in the queue), otherwise
from the last persisted cursor, via ?cursor=<time_us> — and prints
"reconnect after Ns, resuming from seq=<..>" on every reconnect. A
cursor reconnect that is rejected or produces no output for >60s falls
back to a fresh connection without the cursor (with a warning).

Counters: every received message increments `seen` and lands in exactly
one of skipped_dup / kept / dropped_lang / dropped_short / dropped_reply
/ dropped_other, so skipped_dup + kept + dropped_lang + dropped_short +
dropped_reply + dropped_other always sum to seen. A malformed message
increments dropped_other with a
one-line note on stderr; it never crashes the loop. Every kept post then
either enters the queue or is dropped by backpressure; queued posts are
scored (counted in `scored`, one log line each) or, when score() fails on
two attempts, counted in `score_errors` and skipped (no log line).
"""
import argparse
import asyncio
import contextlib
import inspect
import io
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from laya_sort import config, laya

POST_COLLECTION = "app.bsky.feed.post"

# Per-run counters. `seen` counts every received message; every message
# lands in exactly one dropped_* bucket (the first failed check owns it),
# so skipped_dup + kept + dropped_lang + dropped_short + dropped_reply +
# dropped_other always sum to seen. Kept posts then either enter the
# bounded queue or are dropped by backpressure: kept = queued, and queued
# posts end up in `scored` or `score_errors`.
COUNTERS = Counter(
    seen=0,
    skipped_dup=0,
    kept=0,
    dropped_lang=0,
    dropped_short=0,
    dropped_reply=0,
    dropped_other=0,
    dropped_backpressure=0,
    scored=0,
    score_errors=0,
)
_COUNTER_ORDER = ("seen", "skipped_dup", "kept", "dropped_lang",
                  "dropped_short", "dropped_reply", "dropped_other",
                  "dropped_backpressure", "scored", "score_errors")


def counters_report():
    """The counters as a single summary line, e.g.
    seen=1832 skipped_dup=0 kept=412 dropped_lang=201 dropped_short=1187 dropped_reply=22 dropped_other=0
    """
    return " ".join("%s=%d" % (k, COUNTERS[k]) for k in _COUNTER_ORDER)


def _drop_other(note):
    COUNTERS["dropped_other"] += 1
    print("dropped_other: %s" % note, file=sys.stderr)


# ---------------------------------------------------------------------------
# Step 11: cursor resume + reconnect + dedupe
# ---------------------------------------------------------------------------

RECONNECT_BACKOFF_MAX = 30.0  # cap for the exponential reconnect backoff
STALL_SECONDS = 60.0          # cursor reconnect with no output for >this -> fresh fallback


def _load_cursor():
    """Load the persisted stream position from config.CURSOR_PATH.

    Returns {"seq": <last seq>, "time_us": <last time_us>}; zeros (a fresh
    start) when the file is missing, unreadable or malformed.
    """
    try:
        with open(config.CURSOR_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {"seq": int(data["seq"]), "time_us": int(data["time_us"])}
    except (OSError, ValueError, TypeError, KeyError):
        return {"seq": 0, "time_us": 0}


# The persisted stream position, loaded once at import time. last_seq /
# last_time_us are the position of the last successful decision-log append
# (the resume point on a fresh start); seq_next is the next stream index to
# hand out. seq is self-maintained (the wire carries no seq field — time_us
# is the only ordering key) and the persisted cursor advances only when a
# post is actually appended to the decision log. last_read_time_us /
# last_read_seq track the in-process read head (the last message received,
# kept or dropped): posts read but not yet appended still sit in the queue,
# so an in-process reconnect resumes at the read head, not at the persisted
# cursor, to avoid re-fetching and re-enqueuing them. dedup_threshold is the
# resume point set at each (re)connect: a message with time_us at or below
# it is a duplicate (the server redelivers the message AT the cursor).
_cursor = _load_cursor()
_state = {
    "last_seq": _cursor["seq"],
    "last_time_us": _cursor["time_us"],
    "seq_next": _cursor["seq"] + 1,
    "last_read_time_us": 0,
    "last_read_seq": _cursor["seq"],
    "dedup_threshold": _cursor["time_us"],
}


def _persist_cursor(seq, time_us):
    """Atomically persist the stream position after a successful
    decision-log append: write to a per-process tmp file
    (<CURSOR_PATH>.tmp.<pid>), os.replace. The tmp name is unique per
    process because several processes may persist to the same cursor file
    concurrently (daemon + one-shot runs); a shared tmp name let one
    process's os.replace steal another's half-written file. os.replace is
    atomic, and the cursor only ever moves backwards between concurrent
    writers (the inclusive dedupe then re-fetches and skips — never a
    duplicate or a loss)."""
    final = Path(config.CURSOR_PATH)
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path("%s.tmp.%d" % (config.CURSOR_PATH, os.getpid()))
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps({"seq": seq, "time_us": time_us}))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, final)
    _state["last_seq"] = seq
    _state["last_time_us"] = time_us


def _process(raw):
    """Parse + dedupe + pre-filter one raw Jetstream message.

    Increments `seen` and lands the message in exactly one of
    skipped_dup / kept / dropped_*: a resume duplicate (wire time_us at or
    before the last persisted cursor) is skipped — counted in skipped_dup,
    no per-skip line (debug level); every other message is assigned the
    next stream seq. Returns the post dict (stamped with seq and time_us)
    when kept, else None. Never raises.
    """
    COUNTERS["seen"] += 1
    try:
        msg = json.loads(raw)
        if not isinstance(msg, dict):
            _drop_other("message is not a JSON object")
            return None

        # Resume dedupe: time_us is the only ordering key Jetstream sends
        # (the Step 08 probe found no seq field). Verified against the
        # live server: ?cursor=<time_us> resumes inclusively and
        # redelivers the message AT the cursor, so a message at or before
        # the resume point (dedup_threshold) is a duplicate: counted in
        # skipped_dup, no per-skip line (debug level). The read head
        # advances on every received message, kept or dropped.
        time_us = msg.get("time_us")
        if (not isinstance(time_us, int) or isinstance(time_us, bool)
                or time_us <= 0):
            time_us = 0
        if time_us > _state["last_read_time_us"]:
            _state["last_read_time_us"] = time_us
        if time_us and time_us <= _state["dedup_threshold"]:
            COUNTERS["skipped_dup"] += 1
            return None

        seq = _state["seq_next"]
        _state["seq_next"] += 1
        _state["last_read_seq"] = seq

        commit = msg.get("commit")
        if not isinstance(commit, dict):
            _drop_other("no commit object (kind=%r)" % (msg.get("kind"),))
            return None

        # Belt-and-braces: the wantedCollections URL already filters these.
        if commit.get("collection") != POST_COLLECTION:
            _drop_other("collection=%r" % (commit.get("collection"),))
            return None
        if commit.get("operation") != "create":
            _drop_other("operation=%r is not a create" % (commit.get("operation"),))
            return None

        did = msg.get("did")
        rkey = commit.get("rkey")
        cid = commit.get("cid")
        record = commit.get("record")
        if not isinstance(did, str) or not did:
            _drop_other("missing or invalid did")
            return None
        if not isinstance(rkey, str) or not rkey:
            _drop_other("missing or invalid commit.rkey")
            return None
        if not isinstance(cid, str) or not cid:
            _drop_other("missing or invalid commit.cid")
            return None
        if not isinstance(record, dict):
            _drop_other("missing or invalid commit.record")
            return None

        text = record.get("text")
        if not isinstance(text, str):
            _drop_other("missing or non-string record.text")
            return None

        langs = record.get("langs")
        if not isinstance(langs, list):
            langs = []

        # Keep-rule, checked in spec order; the first failed check owns
        # the bucket, so every drop lands in exactly one.
        if not set(langs) & config.LANGS:
            COUNTERS["dropped_lang"] += 1
            return None
        if len(text) < config.MIN_TEXT_LEN:
            COUNTERS["dropped_short"] += 1
            return None
        if record.get("reply") is not None:
            COUNTERS["dropped_reply"] += 1
            return None

        # Creation time: the record's own createdAt, falling back to the
        # message-level time_us field (the Step 08 observed time field).
        created_at = record.get("createdAt")
        if not isinstance(created_at, str) or not created_at:
            created_at = msg.get("time_us")

        post = {
            "uri": "at://%s/%s/%s" % (did, POST_COLLECTION, rkey),
            "cid": cid,
            "text": text,
            "langs": langs,
            "author": did,
            "created_at": created_at,
            "reply": None,
            "seq": seq,
            "time_us": time_us,
        }
        COUNTERS["kept"] += 1
        return post
    except Exception as e:
        _drop_other("unexpected: %s: %s" % (type(e).__name__, e))
        return None


def _jetstream_url():
    return (config.JETSTREAM_URL
            + "?wantedCollections=" + ",".join(config.WANTED_COLLECTIONS))


async def _read_until_closed(ws, deadline, on_post, stall_fallback=False):
    """Read messages from ws until the deadline (returns ("deadline",
    got_msg)), a STALL_SECONDS silence on a cursor connection (returns
    ("stall", got_msg), when stall_fallback), or the connection closes
    (raises — the caller's retry loop owns reconnects). Every message
    goes through _process; on_post (sync or async) is called for every
    kept post. Never raises for malformed messages."""
    loop = asyncio.get_running_loop()
    got_msg = False
    while True:
        remaining = (deadline - loop.time()) if deadline is not None else None
        if remaining is not None and remaining <= 0:
            return "deadline", got_msg
        timeout = (min(remaining, STALL_SECONDS)
                   if remaining is not None else STALL_SECONDS)
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            if remaining is not None and loop.time() >= deadline:
                return "deadline", got_msg
            if not got_msg and stall_fallback:
                return "stall", got_msg
            continue
        got_msg = True
        post = _process(raw)
        if post is not None:
            await _call(on_post, post)


async def _call(handler, post):
    """Invoke handler(post); supports sync and async handlers."""
    result = handler(post)
    if inspect.isawaitable(result):
        await result


async def consume(handler, seconds=None):
    """Connect to Jetstream and feed kept posts to `handler` (Step 09 API).

    `handler` receives one post dict per message that passes the
    pre-filters (sync or async). With `seconds` set, stops reading after
    that many seconds; otherwise reads until the connection closes.
    Counter updates happen per message, inside _process. One connection,
    no reconnect (the daemon path, run(), reconnects with cursor resume);
    resumes from the last persisted cursor when one exists.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds if seconds is not None else None
    resume_from = _state["last_time_us"]
    url = _jetstream_url()
    if resume_from > 0:
        url += "&cursor=%d" % resume_from
    _state["dedup_threshold"] = resume_from
    try:
        async with connect(url, open_timeout=30) as ws:
            await _read_until_closed(ws, deadline, handler)
    except ConnectionClosed:
        # A closed connection is the normal end of the read window when
        # seconds=None ("read until the connection closes").
        return


# ---------------------------------------------------------------------------
# Step 10: bounded queue + scoring consumer
# ---------------------------------------------------------------------------

def _enqueue(queue, post):
    """Push a kept post, stamped with its receive time, onto the bounded
    queue.

    Synchronous: if the queue is full the post is dropped and counted in
    dropped_backpressure. The reader never awaits on a full queue (the WS
    read loop must never block on the consumer) and a dropped post is
    never remembered or retried.
    """
    try:
        queue.put_nowait((time.monotonic(), post))
    except asyncio.QueueFull:
        COUNTERS["dropped_backpressure"] += 1


async def _put_sentinel(queue):
    """Put the None sentinel after all real items, once the queue has room.

    The queue may still be full while the consumer drains it; the sentinel
    is the only thing in this pipeline that ever awaits on a full queue.
    """
    while True:
        try:
            queue.put_nowait(None)
            return
        except asyncio.QueueFull:
            await asyncio.sleep(0.01)


async def _reader(queue, seconds=None):
    """WS read loop with reconnect + cursor resume (Step 11): parse +
    pre-filter, push kept posts onto the queue.

    The resume point for each (re)connect is the in-process read head
    once any message has been received — posts read but not yet appended
    still sit in the queue, so resuming there avoids re-fetching and
    re-enqueuing them — otherwise the last persisted cursor. While the
    resume point is nonzero, the URL carries ?cursor=<resume time_us> and
    the dedupe threshold is set to it, so the inclusive re-delivery of
    the message AT the cursor is skipped.

    On disconnect: backoff 1s -> 2s -> 4s -> ... capped at 30s, then
    reconnect, printing "reconnect after Ns, resuming from seq=<..>" on
    every reconnect. A cursor reconnect that is rejected (the connection
    ends without delivering a single message) or that produces no output
    for >60s falls back to a fresh connection without the cursor (with a
    warning); the cursor is retried on the following reconnect. When the
    read window is over, puts the sentinel so the consumer can drain and
    exit.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds if seconds is not None else None
    backoff = 1.0
    reconnects = 0
    skip_cursor = False
    while True:
        if deadline is not None and loop.time() >= deadline:
            break
        wait = 0.0
        if reconnects:
            wait = backoff
            await asyncio.sleep(wait)
            backoff = min(backoff * 2.0, RECONNECT_BACKOFF_MAX)
        if deadline is not None and loop.time() >= deadline:
            break
        if _state["last_read_time_us"] > 0:
            resume_from = _state["last_read_time_us"]
            resume_seq = _state["last_read_seq"]
        else:
            resume_from = _state["last_time_us"]
            resume_seq = _state["last_seq"]
        use_cursor = resume_from > 0 and not skip_cursor
        skip_cursor = False
        url = _jetstream_url()
        if use_cursor:
            url += "&cursor=%d" % resume_from
        _state["dedup_threshold"] = resume_from
        if wait:
            print("reconnect after %ds, resuming from seq=%d"
                  % (int(wait), resume_seq), file=sys.stderr)
        read_head_before = _state["last_read_time_us"]
        try:
            async with connect(url, open_timeout=30) as ws:
                reason, _ = await _read_until_closed(
                    ws, deadline, lambda post: _enqueue(queue, post),
                    stall_fallback=use_cursor)
            got_msg = _state["last_read_time_us"] > read_head_before
            if got_msg:
                backoff = 1.0  # a connection that delivered messages resets the streak
            if reason == "deadline":
                break
            # reason == "stall": the cursor reconnect had no output for
            # >STALL_SECONDS (Do NOT: fall back to a fresh connection).
            print("warning: cursor resume produced no output for >%ds; "
                  "falling back to fresh connection (no cursor)"
                  % int(STALL_SECONDS), file=sys.stderr)
            skip_cursor = True
        except Exception as e:
            got_msg = _state["last_read_time_us"] > read_head_before
            if got_msg:
                backoff = 1.0
            print("jetstream disconnected: %s: %s"
                  % (type(e).__name__, e), file=sys.stderr)
            if use_cursor and not got_msg:
                print("warning: cursor resume rejected (no messages before "
                      "disconnect); falling back to fresh connection (no cursor)",
                      file=sys.stderr)
                skip_cursor = True
            if deadline is not None and loop.time() >= deadline:
                break
        reconnects += 1
    await _put_sentinel(queue)


async def _score_post(post):
    """Score one post in a worker thread: score() is blocking torch work
    and must NOT run on the event loop (it would freeze the WS reader).

    Returns the verdict dict, or None when score() fails on two attempts
    (the first try plus at most one retry — never more; the caller counts
    it in score_errors and keeps going).
    """
    for attempt in (1, 2):
        try:
            return await asyncio.to_thread(laya.score, post)
        except Exception as e:
            if attempt == 2:
                print("score_errors: uri=%s %s: %s"
                      % (post.get("uri"), type(e).__name__, e),
                      file=sys.stderr)
    return None


async def _consumer(queue, latencies):
    """Pop posts, score them in a thread, append one JSON line to the log.

    Each scored post appends its verdict dict plus latency_ms (monotonic
    receive -> scored, in ms), scored_at (wall clock, UTC) and the stream
    position (seq, time_us) to config.LOG_PATH in append mode, flushed per
    line. After each successful append the stream position is persisted
    atomically to config.CURSOR_PATH (write .tmp, os.replace) — the cursor
    never gets ahead of the log. Latencies are recorded in `latencies` for
    the status lines and the final report. Posts that fail to score are
    counted in score_errors and skipped (no log line). Exits on the None
    sentinel.
    """
    log_path = Path(config.LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        item = await queue.get()
        if item is None:
            return
        recv_monotonic, post = item
        verdict = await _score_post(post)
        if verdict is None:
            COUNTERS["score_errors"] += 1
            continue
        latency_ms = (time.monotonic() - recv_monotonic) * 1000
        latencies.append(latency_ms)
        record = dict(verdict)
        record["latency_ms"] = round(latency_ms, 2)
        record["scored_at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        record["seq"] = post["seq"]
        record["time_us"] = post["time_us"]
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
            f.flush()
        COUNTERS["scored"] += 1
        _persist_cursor(post["seq"], post["time_us"])


def _percentile(values, pct):
    """Nearest-rank percentile (pct in 0..100) of `values`; 0.0 if empty."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[rank - 1]


def status_line(queue, latencies):
    """One status line (Step 10 contract):
    queue=<depth> seen=.. kept=.. dropped_bp=.. scored=.. p50_lat_ms=..
    """
    return ("queue=%d seen=%d kept=%d dropped_bp=%d scored=%d p50_lat_ms=%.1f"
            % (queue.qsize(), COUNTERS["seen"], COUNTERS["kept"],
               COUNTERS["dropped_backpressure"], COUNTERS["scored"],
               _percentile(latencies, 50)))


async def _status_lines(queue, latencies, period=10.0):
    """Print one status line to stderr every `period` seconds (forever;
    the caller cancels it). Stderr, so a piped stdout stays clean."""
    while True:
        await asyncio.sleep(period)
        print(status_line(queue, latencies), file=sys.stderr)


def final_report(latencies):
    """The final report: all counters + latency median/p90 (the scored
    count is one of the counters)."""
    return ("%s p50_lat_ms=%.1f p90_lat_ms=%.1f"
            % (counters_report(), _percentile(latencies, 50),
               _percentile(latencies, 90)))


async def run(seconds=None):
    """Reader + bounded queue + scoring consumer, for `seconds`
    (None = read until the connection closes).

    The reader reconnects with cursor resume on disconnect (Step 11).
    Runs the reader, the consumer and the 10s status-line task
    concurrently; when the reader is done it puts the sentinel, the
    consumer drains the queue and exits. Prints the final report to
    stdout.
    """
    queue = asyncio.Queue(maxsize=config.QUEUE_MAX)
    latencies = []  # per-post latency_ms, filled by the consumer
    Path(config.LOG_PATH).parent.mkdir(parents=True, exist_ok=True)

    status_task = asyncio.create_task(_status_lines(queue, latencies))
    reader_task = asyncio.create_task(_reader(queue, seconds))
    consumer_task = asyncio.create_task(_consumer(queue, latencies))
    try:
        await reader_task
        await consumer_task
    finally:
        for task in (status_task, consumer_task):
            if not task.done():
                task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.gather(status_task, consumer_task)

    print(final_report(latencies))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="laya_sort.jetstream",
        description="Laya Sky Feed: Jetstream reader (reconnect + cursor "
                    "resume) + bounded queue + scoring consumer (Step 11).")
    parser.add_argument("--seconds", type=int, default=None,
                        help="stop reading after N seconds "
                             "(default: read until the connection closes)")
    args = parser.parse_args(argv)
    # Load the RL agent up front, on the main thread, so the worker threads
    # never race on the lazy init. stdout is reserved for the final report,
    # so the device line goes to stderr (same treatment as the CLI).
    load_log = io.StringIO()
    with contextlib.redirect_stdout(load_log):
        laya.get_agent()
    if load_log.getvalue():
        sys.stderr.write(load_log.getvalue())
        sys.stderr.flush()
    try:
        asyncio.run(run(seconds=args.seconds))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
