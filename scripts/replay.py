"""Step 07: replay.py — offline re-scoring + determinism proof.

The A/B workhorse: re-score any saved posts file (JSON array or JSONL)
offline, deterministically, via laya.score(). No network, no timestamps,
agent singleton loaded once for the whole run. Identical input posts must
produce byte-identical output (that property is what Step 12's live check
depends on).

Run from the repo root:
    python scripts/replay.py --in fixtures/posts_v1.json --out data/replay_a.jsonl
"""
import argparse
import contextlib
import io
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from laya_sort import laya  # noqa: E402
from laya_sort.cli import read_posts  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="replay",
        description="Offline re-scoring: posts file (JSON array or JSONL) "
                    "-> one JSON verdict line per post.")
    parser.add_argument("--in", dest="in_file", required=True, metavar="POSTS",
                        help="input posts file (JSON array or JSONL)")
    parser.add_argument("--out", required=True, metavar="VERDICTS_JSONL",
                        help="output file, one JSON verdict per line")
    args = parser.parse_args(argv)

    try:
        posts = read_posts(args.in_file)
    except (OSError, ValueError) as e:
        print("replay: %s" % e, file=sys.stderr)
        return 1

    # laya.get_agent() prints its load line to stdout; stdout is reserved for
    # this tool's own output, so capture it and echo it to stderr (as the CLI does).
    load_log = io.StringIO()
    with contextlib.redirect_stdout(load_log):
        laya.get_agent()
    if load_log.getvalue():
        sys.stderr.write(load_log.getvalue())
        sys.stderr.flush()

    with open(args.out, "w", encoding="utf-8") as out:
        for post in posts:
            out.write(json.dumps(laya.score(post)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
