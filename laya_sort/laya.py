"""Scoring core: the only place Laya is invoked.

`score(post) -> verdict` is pure and deterministic: no timestamps, no randomness,
no I/O inside the payload, and always a fresh forward pass (no verdict caching).
The CLI, the replay tool, and the daemon all import this module; replay requires
byte-identical verdicts for identical posts.
"""
import os
import sys

from laya_sort import config
from laya_sort.questions import QUESTION_SET, QUESTION_SET_VERSION

# STATE_SCHEMA (Step 04): system_one(state, ...) accepts `state` as a str (used
# verbatim) or any JSON-serializable object (json.dumps, ensure_ascii=False).
# We pass the post text as a str — the minimal input that matches the question
# ("does this post contain...") and the vendor README quickstart shape.
QUALITY_QID = "quality"

_agent = None


def _repo_root():
    # laya_sort/laya.py -> repo root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_agent():
    """Load the vendor RL agent exactly once (module-level lazy singleton)."""
    global _agent
    if _agent is None:
        # Same sys.path trick as scripts/smoke_test.py: vendor dir on the path,
        # vendor code imported in place, never modified.
        sys.path.insert(0, os.path.join(_repo_root(), "models", "laya"))
        import rl_agent_api
        _agent = rl_agent_api.RLAgent(config.MODEL_DIR, device=config.DEVICE)
        print("device=%s checkpoint=%s" % (config.DEVICE, config.MODEL_DIR))
    return _agent


def score(post: dict) -> dict:
    """Score one post. Deterministic for identical input posts (replay-safe)."""
    agent = get_agent()
    state = post["text"]
    result = agent.system_one(state, QUESTION_SET)
    ans = result["answers"][QUALITY_QID]
    verdict = ans["choice"]
    assert verdict in QUESTION_SET[QUALITY_QID]["criteria"], "unexpected verdict %r" % (verdict,)
    return {
        "uri": post["uri"],
        "author": post.get("author", ""),
        "created_at": post.get("created_at", ""),
        "verdict": verdict,
        "probabilities": ans["probabilities"],
        "confidence": ans["confidence"],
        "question_set": QUESTION_SET_VERSION,
    }
