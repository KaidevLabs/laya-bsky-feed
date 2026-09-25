# Step 01 — venv + dependencies (CPU)

phase: env · machine: laptop (plain Linux) · depends: nothing

## Goal
A working venv with every runtime dependency installed. CPU-only torch.

## Start state
Repo at `~/Documents/laya-sort` containing `README.md`, `plans/`, and a `.venv` that already has `huggingface_hub` installed.

## Do
1. `cd ~/Documents/laya-sort && source .venv/bin/activate`
2. Install:
```bash
pip install torch transformers safetensors numpy websockets fastapi "uvicorn[standard]"
```
- No `--index-url` for torch: plain PyPI wheels are CPU builds on this machine.
- `huggingface_hub` is already installed; pip will keep it as-is.

## Files you may touch
- none (environment only)

## Accept
```bash
python -c "import torch, transformers, safetensors, numpy, websockets, fastapi; print('deps ok', torch.__version__)"
python -c "import torch; print('cuda_available:', torch.cuda.is_available())"
```
- Line 1 prints `deps ok <version>`.
- Line 2 prints `cuda_available: False` — expected on this laptop.

## Do NOT
- Install CUDA/cu128 torch on this machine (that is Step 16, desktop only).
- Create any project source files (Step 03 does that).
- Upgrade or pin `huggingface_hub` to a different version.
- Report success without running both Accept commands.
