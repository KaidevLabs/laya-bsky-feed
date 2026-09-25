"""Step 08: connect to Jetstream, print 10 raw messages, record observed field names.

Run from the repo root:  python scripts/jetstream_probe.py
Finds: union of top-level keys, `commit` sub-keys, and `commit.collection` values.
Writes: data/probe_fields.json
"""
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from laya_sort import config  # noqa: E402
from websockets.sync.client import connect  # noqa: E402

N_MESSAGES = 10
OPEN_TIMEOUT = 30  # seconds to establish the WebSocket
RECV_TIMEOUT = 45  # seconds to wait for each message; generous: the CPU box is slow


def main():
    url = config.JETSTREAM_URL + "?wantedCollections=" + ",".join(config.WANTED_COLLECTIONS)
    print("connecting to:", url)

    top_level_keys = set()
    commit_keys = set()
    collections = set()
    sample_message = None

    try:
        with connect(url, open_timeout=OPEN_TIMEOUT) as ws:
            print("connected, waiting for messages")
            for i in range(N_MESSAGES):
                raw = ws.recv(timeout=RECV_TIMEOUT)
                print("msg %d/%d: %s" % (i + 1, N_MESSAGES, json.dumps(raw)[:300]))
                data = json.loads(raw)
                if sample_message is None:
                    sample_message = data
                if isinstance(data, dict):
                    top_level_keys.update(data.keys())
                    commit = data.get("commit")
                    if isinstance(commit, dict):
                        commit_keys.update(commit.keys())
                        if "collection" in commit:
                            collections.add(commit["collection"])
    except Exception as e:
        print("PROBE FAILED: %s: %s" % (type(e).__name__, e))
        sys.exit(1)

    findings = {
        "top_level_keys": sorted(top_level_keys),
        "commit_keys": sorted(commit_keys),
        "collections": sorted(collections),
        "sample_message": sample_message,
    }
    out_path = os.path.join(_REPO_ROOT, "data", "probe_fields.json")
    with open(out_path, "w") as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("wrote %s" % out_path)
    print("top_level_keys:", sorted(top_level_keys))
    print("commit_keys:", sorted(commit_keys))
    print("collections:", sorted(collections))


if __name__ == "__main__":
    main()
