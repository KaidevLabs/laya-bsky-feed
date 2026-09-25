# Step 14 — dashboard/index.html (the live view)

phase: ui · machine: laptop · depends: step-13

## Goal
One HTML file — zero build step, zero CDNs, fully offline — showing posts + verdicts as they are scored.

## Do
1. Create `dashboard/index.html`:
   - On load: `fetch('/history?n=20')` → render those cards first. Then `const es = new EventSource('/stream');` and `es.onmessage = e => prependCard(JSON.parse(e.data))`.
   - Each card shows: `text` (max 3 lines, CSS line-clamp), `@author`, relative `created_at`, a verdict chip (A → green "show", B → gray "noise"), a thin horizontal probability bar split A/B, and the confidence %.
   - Cap the DOM at 50 cards — when the 51st arrives, remove the oldest (a long run must not eat memory).
   - Plain CSS inside a `<style>` tag. No frameworks, no external requests, no build tooling. Keep the whole file ≤ ~150 lines.
2. EventSource reconnects on its own — do not write custom reconnect logic (Step 15 tests exactly that).

## Files
- create `dashboard/index.html`

## Accept
1. Daemon running (Step 13). Open `http://127.0.0.1:8000` in a browser.
2. History cards render immediately on load; new cards appear as posts get scored; bar widths visually match the `probabilities` in the corresponding log line (spot-check 3).

## Do NOT
- Add npm, bundlers, Tailwind CDN, fonts from the network — the page must work with the machine fully offline.
- Poll `/history` in a loop — SSE is the live channel; history is load-time only.
