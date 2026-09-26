"""Step 09: read the Jetstream firehose for 60s, print the counter report.

Run from the repo root:  python scripts/run_reader.py

Runs laya_sort.jetstream.consume with a counting handler for 60 seconds,
then prints the single counters_report() line (the only thing written to
stdout). Malformed messages increment dropped_other with a one-line note
on stderr; nothing else goes to stdout.
"""
import asyncio
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from laya_sort import jetstream  # noqa: E402

SECONDS = 60

_kept_posts = []


async def counting_handler(post):
    """Collect the kept posts the consumer hands us."""
    _kept_posts.append(post)


def main():
    asyncio.run(jetstream.consume(counting_handler, seconds=SECONDS))
    if len(_kept_posts) != jetstream.COUNTERS["kept"]:
        print("run_reader: handler saw %d posts but the kept counter is %d"
              % (len(_kept_posts), jetstream.COUNTERS["kept"]), file=sys.stderr)
    print(jetstream.counters_report())


if __name__ == "__main__":
    main()
