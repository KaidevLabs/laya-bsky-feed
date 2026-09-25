"""Laya Sky Feed CLI (Step 06).

Usage (from the repo root):
    python -m laya_sort.cli score <posts_file> [--out OUT]

`score` reads a JSON array file or a JSONL file of post dicts, scores each
post via laya.score(), and writes one JSON verdict line per post to stdout
(or to --out when given). Nothing else is written to stdout while scoring;
logs go to stderr.

`build-index` and `top` are reserved names: they raise
NotImplementedError("added in Step 19") until Step 19 fills them in.
"""
import argparse
import contextlib
import io
import json
import sys

from laya_sort import laya


def read_posts(path):
    """Parse `path` as a JSON array of post dicts, or as JSONL of post dicts.

    One parser for both shapes: try json.loads on the whole file (a JSON
    array); on failure, parse line by line. Raises ValueError with a
    descriptive message on bad input.
    """
    with open(path, encoding="utf-8") as f:
        content = f.read()
    try:
        posts = json.loads(content)
    except json.JSONDecodeError:
        posts = []
        for lineno, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                posts.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError("%s:%d: not a JSON array of post dicts nor JSONL: %s"
                                 % (path, lineno, e)) from e
    if not isinstance(posts, list):
        raise ValueError("%s: expected a JSON array of post dicts, got %s"
                         % (path, type(posts).__name__))
    for i, post in enumerate(posts):
        if not isinstance(post, dict):
            raise ValueError("%s: post #%d is not a dict" % (path, i))
    return posts


def cmd_score(args):
    try:
        posts = read_posts(args.posts_file)
    except (OSError, ValueError) as e:
        print("laya_sort.cli: %s" % e, file=sys.stderr)
        return 1

    # laya.get_agent() prints its load line to stdout; stdout is reserved for
    # verdict lines, so capture it and echo it to stderr.
    load_log = io.StringIO()
    with contextlib.redirect_stdout(load_log):
        laya.get_agent()
    if load_log.getvalue():
        sys.stderr.write(load_log.getvalue())
        sys.stderr.flush()

    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    try:
        for post in posts:
            out.write(json.dumps(laya.score(post)) + "\n")
        out.flush()
    finally:
        if args.out:
            out.close()
    return 0


def cmd_build_index(args):
    raise NotImplementedError("added in Step 19")


def cmd_top(args):
    raise NotImplementedError("added in Step 19")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="laya_sort.cli",
        description="Laya Sky Feed: score Bluesky posts with Laya.")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_score = sub.add_parser(
        "score",
        help="score a posts file (JSON array or JSONL) -> one JSON verdict line per post")
    p_score.add_argument("posts_file",
                         help="path to a JSON array or JSONL file of post dicts")
    p_score.add_argument("--out",
                         help="write the verdict lines to this file instead of stdout")
    p_score.set_defaults(func=cmd_score)

    p_build_index = sub.add_parser(
        "build-index",
        help="(reserved, added in Step 19)")
    p_build_index.set_defaults(func=cmd_build_index)

    p_top = sub.add_parser(
        "top",
        help="(reserved, added in Step 19)")
    p_top.set_defaults(func=cmd_top)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except NotImplementedError as e:
        print("laya_sort.cli: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
