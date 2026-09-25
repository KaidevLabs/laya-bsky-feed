# Step 20 — XRPC: describeFeedGenerator + getFeedSkeleton

phase: feed · machine: laptop · depends: step-19

## Goal
Spec-shaped feed-generator endpoints over the index. Local only — going public is Step 22's gate.

## Do
1. Add to `laya_sort/config.py`: `DID = os.environ.get("LAYA_DID", "did:web:example.com")` (placeholder until Step 22) and `FEED_NAME = os.environ.get("LAYA_FEED_NAME", "laya-sky")`.
2. Create `laya_sort/server.py`:
   - `GET /xrpc/app.bsky.feed.describeFeedGenerator` →
     `{"did": config.DID, "feeds": [{"uri": f"at://{config.DID}/app.bsky.feed.generator/{config.FEED_NAME}"}]}`
   - `GET /xrpc/app.bsky.feed.getFeedSkeleton?feed=&limit=&cursor=` →
     `{"feed": [{"post": "at://..."} ...], "cursor": "<opaque next>"}`.
     Cursor = `"<last_confidence>|<last_uri>"` keyset pagination on the index; limit clamped to 1..100 (default 50 — state the default in the docstring).
   - Match the official shapes: https://github.com/bluesky-social/atproto/blob/main/docs/specs/xrpc.md and the feed-generator guide (https://blueskybook.dev/atproto/feed.html). Unknown query params are ignored; `feed` param mismatching our URI → 404 JSON error.
3. Mount these routes in `daemon.py` (same app, same port — include the router).

## Files
- create `laya_sort/server.py`
- edit `laya_sort/config.py` (the two keys), `laya_sort/daemon.py` (mount router)

## Accept
```bash
curl -s "http://127.0.0.1:8000/xrpc/app.bsky.feed.describeFeedGenerator" | python -m json.tool
curl -s "http://127.0.0.1:8000/xrpc/app.bsky.feed.getFeedSkeleton?limit=5" | python -m json.tool
# take the returned cursor and ask for the next page:
curl -s "http://127.0.0.1:8000/xrpc/app.bsky.feed.getFeedSkeleton?limit=5&cursor=<returned>" | python -m json.tool
```
- Shapes match the spec; posts are AT-URIs present in the index; pages do not overlap; `limit=500` silently clamps to 100.

## Do NOT
- Implement `getServiceAuth` yet (Step 21) — and do NOT reject unauthenticated calls "for safety" here; enforcement lands in Step 21.
- Invent response fields beyond the spec.
