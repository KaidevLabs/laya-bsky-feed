# Step 21 — service auth: verify AppView-signed requests

phase: feed · machine: laptop · depends: step-20

## Goal
The skeleton endpoint serves only verified callers. Bluesky's AppView signs requests; we check the JWT before touching the index. A public feed without this gets flagged by the network — no "demo mode".

## Do
1. Per the ATProto service-auth spec: requests carry `Authorization: Bearer <JWT>`; the JWT's issuer is a `did:plc:...` (the requester's PDS); verify the signature against that DID doc's rotation key (resolve via PLC directory, `config.PLC_URL = "https://plc.directory"` — add to config), and check `aud` equals our service DID.
2. Enforce on `getFeedSkeleton`. Add `getServiceAuth` advertising endpoint if the spec requires it (check the docs page linked in Step 20).
3. Use a maintained JWT library (PyJWT). Never hand-roll signature checks.
4. Cache DID-document resolutions for ~5 minutes (PLC lookups per request would be rude); cache is in-memory only.

## Files
- edit `laya_sort/server.py`, `laya_sort/config.py` (PLC_URL)

## Accept
```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/xrpc/app.bsky.feed.getFeedSkeleton?limit=5"
# → 401
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer not.a.jwt" "http://127.0.0.1:8000/xrpc/app.bsky.feed.getFeedSkeleton?limit=5"
# → 401
```
- Unsigned and malformed JWTs → 401 with a JSON error body naming the reason.
- The positive path (a genuinely signed request) is verified live in Step 22 — note that explicitly in your report. If the spec permits an offline verification setup (self-generated keypair test), add it as `scripts/check_serviceauth.py` and make it pass.

## Do NOT
- Add a bypass flag, env var, or "demo mode" that skips verification.
- Resolve PLC per request without caching.
