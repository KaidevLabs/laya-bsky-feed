"""Step 05 acceptance: score the v1 fixture twice; require byte-identical verdicts.

Run from the repo root:  python scripts/check_score.py
"""
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from laya_sort.laya import score  # noqa: E402

FIXTURE = os.path.join(_REPO_ROOT, "fixtures", "posts_v1.json")
REQUIRED_KEYS = ["uri", "author", "created_at", "verdict", "probabilities", "confidence", "question_set"]


def main():
    with open(FIXTURE) as f:
        posts = json.load(f)
    assert isinstance(posts, list) and len(posts) == 3, "fixture must be a JSON array of 3 posts"

    run1 = [json.dumps(score(p)) for p in posts]
    run2 = [json.dumps(score(p)) for p in posts]
    assert run1 == run2, "non-deterministic: runs differ:\nRUN1:\n%s\nRUN2:\n%s" % ("\n".join(run1), "\n".join(run2))

    for post, s in zip(posts, run1):
        d = json.loads(s)
        missing = [k for k in REQUIRED_KEYS if k not in d]
        assert not missing, "verdict for %s missing keys: %s" % (post["uri"], missing)

    for post, s in zip(posts, run1):
        d = json.loads(s)
        print("verdict=%s confidence=%s probabilities=%s | %s" % (d["verdict"], d["confidence"], d["probabilities"], post["text"]))
    print("CHECK SCORE PASS")


if __name__ == "__main__":
    main()
