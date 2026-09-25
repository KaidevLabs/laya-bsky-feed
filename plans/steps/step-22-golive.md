# Step 22 — publish the feed record + go live (GATED — requires you)

phase: feed · machine: desktop recommended · depends: step-21, your Bluesky account, a public tunnel

## Goal
The feed exists in the Bluesky app and serves skeletons from your index. This step is gated: it touches your account, so you do the account parts — the agent only preps config.

## Do
1. Host: on the desktop, `LAYA_DEVICE=cuda python -m laya_sort.daemon` (the box that stays on; GPU scoring is live now).
2. Public exposure: `cloudflared tunnel` (or an ngrok static domain) → stable HTTPS URL for the daemon.
3. DID: serve `/.well-known/atproto-did` (plain-text did:web) from that host, plus the DID document advertising the XRPC service endpoint. Set `LAYA_DID=did:web:<your-host>` on the daemon.
4. Account (YOU, not the agent): in Bluesky, create the feed generator record (`app.bsky.feed.generator`) pointing at the DID — the app walks you through it via the custom-feed URL.
5. Follow your own feed, post something, watch the pipeline decide whether it surfaces.

## Accept
- The feed opens in the Bluesky app and returns skeletons end-to-end from a remote, signed client.
- Step-12-style checks pass against the live public endpoint.

## Do NOT
- Let the agent handle your app password, session tokens, or OAuth flow — account steps are yours.
- Go live before Step 21's verification is proven — an unverified public skeleton endpoint will be rejected/flagged.
- Forget the daemon must run under a supervisor on the desktop (this is the one place a `systemd --user` unit becomes worth it — add it if you like, but only here).
