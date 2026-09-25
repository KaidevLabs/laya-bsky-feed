# Step 16 — desktop: CUDA env + model on the 5090 box

phase: gpu · machine: desktop (WSL2 Ubuntu on Windows 11) · depends: nothing (independent of laptop steps)

## Goal
Torch+CUDA working on the RTX 5090, model present, device visible.

## Do
1. Clone/copy the repo onto the Windows machine and open WSL2 Ubuntu in it.
2. `python3 -m venv .venv && source .venv/bin/activate`
3. `pip install torch --index-url https://download.pytorch.org/whl/cu128`
   **PyTorch ≥ 2.7 is required** — sm_120 (Blackwell) has no kernels in older wheels; older cu126 wheels raise "no kernel image is available" at first use.
4. `pip install transformers safetensors numpy websockets fastapi "uvicorn[standard]"`
5. `hf download convaiinnovations/laya --local-dir models/laya`
6. `nvidia-smi` → RTX 5090 visible, driver ≥ 570.
7. Create the same `.gitignore` as Step 03 (models/, data/, .venv/, __pycache__/).

## Files
- environment + `models/laya/**`, `.gitignore`

## Accept
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Prints `True NVIDIA GeForce RTX 5090`.

## Do NOT
- Install a system CUDA toolkit — the wheels bundle their own runtime; only the Windows NVIDIA driver (with WSL support) is needed.
- Accept `False` or a "no kernel image is available" error as "close enough" — that means wrong torch build; report and stop.
- Continue to Step 17 without this Accept passing.
