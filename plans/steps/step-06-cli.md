# Step 06 — CLI: score a posts file

phase: core · machine: laptop · depends: step-05

## Goal
`python -m laya_sort.cli score <file>` → one JSON verdict line per post, on stdout or `--out`.

## Do
1. Create `laya_sort/cli.py` with argparse subcommands:
   - `score <posts_file> [--out OUT]`: input is a JSON array file **or** a JSONL file of post dicts (implement one parser that accepts both: try `json.loads(whole file)` → list; on failure, parse line by line). Scores each post via `laya.score()`, writes one `json.dumps` verdict per line to stdout, or to `--out` when given.
   - `build-index` and `top`: reserve the names now with stubs that raise `NotImplementedError("added in Step 19")` so the CLI surface is stable and Step 19 only fills them.
   - `--help` lists every subcommand.
2. Keep the module importable (`python -m laya_sort.cli --help` works from repo root).

## Files
- create `laya_sort/cli.py`

## Accept
```bash
python -m laya_sort.cli score fixtures/posts_v1.json
```
→ exactly 3 JSON lines, identical content to what `scripts/check_score.py` produced. Exit code 0.

```bash
python -m laya_sort.cli --help
```
→ lists `score`, `build-index`, `top`.

## Do NOT
- Add flags for features that don't exist yet.
- Print anything to stdout other than the verdict lines when scoring (logs go to stderr).
