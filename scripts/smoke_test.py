"""Step 04 smoke test.

Loads the vendor RLAgent on CPU, scores 3 fixed posts, and prints a discovery
record of the exact `system_one` API that step 05 builds on.

Run from the repo root:  LAYA_DEVICE=cpu python scripts/smoke_test.py
"""
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))       # so `laya_sort` is importable
sys.path.insert(0, "models/laya")   # vendor dir on the path; vendor code stays untouched

import laya_sort.config as config
import rl_agent_api

# Three fixed posts as inline literals (do not read files).
POSTS = [
    ("a: billing complaint", "Hi, we were billed twice for March, please refund the duplicate charge."),
    ("b: chit-chat", "coffee was great today, might go again tomorrow"),
    ("c: Spanish", "La aplicación se cierra cada vez que abro la configuración."),
]

# Throwaway questions, shapes exactly as used in the vendor README quickstart.
SMOKE_QUESTIONS = {
    "show": {
        "type": "choice",
        "instructions": "Which category does this post fall into?",
        "criteria": {
            "A": "a substantive post worth showing",
            "B": "chit-chat or noise",
        },
    },
    "complaint": {
        "type": "noul",
        "instructions": "Does this post report a problem or complaint about a product or service?",
    },
}


def load_agent():
    """Load the root (English) checkpoint; retry with typed-decisions if the root load raises."""
    try:
        return rl_agent_api.RLAgent(config.MODEL_DIR, device=config.DEVICE), config.MODEL_DIR
    except Exception as e:
        print("root checkpoint %r failed to load: %r; retrying models/laya/typed-decisions"
              % (config.MODEL_DIR, e))
    fallback = "models/laya/typed-decisions"
    return rl_agent_api.RLAgent(fallback, device=config.DEVICE), fallback


def main():
    # --- 1. Discovery info FIRST, before loading weights -------------------------
    print("=== discovery: RLAgent.system_one ===")
    print("signature:", inspect.signature(rl_agent_api.RLAgent.system_one))
    print("docstring:", (rl_agent_api.RLAgent.system_one.__doc__ or "").strip())
    with open(Path(config.MODEL_DIR) / "rl_agent_config.json") as f:
        cfg = json.load(f)
    print("config: max_len=%s head_max_len=%s encoder=%s"
          % (cfg["max_len"], cfg["head_max_len"], cfg["encoder"]))

    # --- 2. Load the agent (root = English checkpoint) ---------------------------
    agent, checkpoint = load_agent()
    print("device=%s checkpoint=%s" % (config.DEVICE, checkpoint))

    # --- 3. Determine the expected state type (step 05 depends on this) ----------
    probe = POSTS[0][1]
    states = {"str": probe, "dict": {"document": probe}}
    state_kind = None
    for kind in ("str", "dict"):
        try:
            agent.system_one(states[kind], SMOKE_QUESTIONS)
            state_kind = kind
            break
        except Exception as e:
            print("state as %s rejected: %r" % (kind, e))
    if state_kind is None:
        print("STATE_SCHEMA=none (both str and dict states were rejected)")
        raise
    other = "dict" if state_kind == "str" else "str"
    other_ok = False
    try:
        agent.system_one(states[other], SMOKE_QUESTIONS)
        other_ok = True
    except Exception:
        pass
    if other_ok:
        print("STATE_SCHEMA=str or dict (non-str state is json.dumps'd by rl_common.serialize_state)")
    else:
        print("STATE_SCHEMA=%s (%s state rejected)" % (state_kind, other))

    # --- 4. Score the three fixed posts -------------------------------------------
    for label, text in POSTS:
        state = text if state_kind == "str" else {"document": text}
        print("\n=== post %s ===" % label)
        result = agent.system_one(state, SMOKE_QUESTIONS)
        print(json.dumps(result["answers"], indent=2, ensure_ascii=False))

    # --- 5. Final line --------------------------------------------------------------
    print("\ndevice=%s checkpoint=%s" % (config.DEVICE, checkpoint))


if __name__ == "__main__":
    main()
