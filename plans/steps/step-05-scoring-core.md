# Step 05 — scoring core: questions v1 + score()

phase: core · machine: laptop · depends: step-04

## Goal
A pure, deterministic `score(post) -> verdict` function plus the versioned question set. This is the module the CLI, the replay tool, and the daemon all import — the only place Laya is invoked.

## Do
1. Create `laya_sort/questions.py`:
```python
# QUESTION_SET_V1 — wording is a design artifact; A/B it later via scripts/replay.py.
# Two-option choice with neutral keys A/B on purpose: the vendor README ("Honest limits")
# warns that yes/no-style labels can hijack the answer.
QUESTION_SET = {
    "quality": {
        "type": "choice",
        "instructions": "Does this social media post contain something worth showing to others (information, art, humor, help), or is it noise?",
        "criteria": {
            "A": "substantive: informs, teaches, shows work, makes a real point, or is genuinely funny",
            "B": "noise: empty chatter, spam, bait, a repost of nothing, or unintelligible",
        },
    },
}
QUESTION_SET_VERSION = "v1"
```
2. Create `laya_sort/laya.py`:
   - Module-level lazy singleton `_agent = None`; `get_agent()` loads `rl_agent_api.RLAgent(config.MODEL_DIR, device=config.DEVICE)` exactly once (same `sys.path` trick as the smoke test) and prints `device=<..> checkpoint=<..>` on first load.
   - `def score(post: dict) -> dict:` builds the state per the schema discovered in Step 04 (the `STATE_SCHEMA=` finding), calls `agent.system_one(state, QUESTION_SET)`, and returns:
```python
{"uri": post["uri"], "author": post.get("author", ""), "created_at": post.get("created_at", ""),
 "verdict": "A" or "B", "probabilities": {...}, "confidence": <float>, "question_set": "v1"}
```
   - NO timestamps inside the verdict payload — determinism for replay is a requirement. Wall-clock belongs to the caller (Step 10 adds it to the log line).
3. Create `fixtures/posts_v1.json`: a JSON **array** of the same 3 posts used by the smoke test, each with keys `uri, cid, text, langs, author, created_at` (plausible values: `at://did:plc:xxx/app.bsky.feed.post/yyy` style uris).
4. Create `scripts/check_score.py`: loads the fixture, scores all 3 posts **twice**, asserts both runs produce byte-identical JSON strings, asserts the required keys exist, prints `CHECK SCORE PASS`.

## Files
- create `laya_sort/questions.py`, `laya_sort/laya.py`, `fixtures/posts_v1.json`, `scripts/check_score.py`

## Accept
```bash
python scripts/check_score.py
```
Prints `CHECK SCORE PASS`. Print the 3 verdicts too — billing post likely `A`, chit-chat likely `B`, Spanish post either (English-only checkpoint; record what it says — that feeds the Step-16 multilingual conversation later).

## Do NOT
- Change question wording without bumping `QUESTION_SET_VERSION` (replay A/B keys off that tag).
- Add timestamps, randomness, or network calls inside `score()`.
- Cache verdicts anywhere — score() is always a fresh forward pass.
