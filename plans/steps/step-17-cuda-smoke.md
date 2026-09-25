# Step 17 — desktop: the same smoke test on CUDA

phase: gpu · machine: desktop · depends: step-16 + repo files from Steps 03–05 (sync from the laptop)

## Goal
The `LAYA_DEVICE` seam proven: the exact same code path answers on GPU. Verdict labels should match the CPU run; float noise may wiggle the decimals.

## Do
1. Sync the repo state from the laptop: `laya_sort/`, `scripts/`, `fixtures/`, `dashboard/`, `plans/` (git push/pull preferred; a folder copy is acceptable). NOT `models/` or `data/` — the desktop has its own.
2. `LAYA_DEVICE=cuda python scripts/smoke_test.py`
3. Compare the 3 verdicts against the laptop's Step-04 output: labels should agree; decimal probabilities may differ slightly (fp16 autocast on GPU vs fp32 CPU — that is D3 working as designed). Record any label flip in your notes.

## Accept
- Output contains `device=cuda checkpoint=...` and, visibly, `NVIDIA GeForce RTX 5090` (add `torch.cuda.get_device_name(0)` to the smoke printout if it isn't already visible).
- 3 answer blocks, exit 0.
- Label agreement with the CPU run recorded (a *systematic* flip on all posts = bug → report; an isolated flip on the Spanish post is a known English-checkpoint limitation, note it).

## Do NOT
- Tune anything to force bit-identical outputs — fp16 autocast is the shipped vendor behavior.
- Switch back to CPU "because it matches better" — the GPU is the point; differences are documented, not eliminated.
