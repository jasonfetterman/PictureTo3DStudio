# Install the local AI engine (Windows)

The desktop interface and export tools are separate from the AI runtime. The first generation requires a compatible NVIDIA GPU, a current NVIDIA driver, and a CUDA-enabled PyTorch installation. Model weights are downloaded on first use and require an internet connection. The exact VRAM requirement depends on model settings and software versions.

## 1. Check your hardware

Open PowerShell and run:

```powershell
nvidia-smi
```

If this command is not recognized, install/update the NVIDIA driver or confirm that the computer has a supported NVIDIA GPU. This initial backend uses CUDA; it does not silently fall back to a paid cloud service.

## 2. Install PyTorch

Activate the application's environment:

```powershell
cd C:\Path\To\PictureTo3DStudio
.\.venv\Scripts\Activate.ps1
```

Install the current CUDA-enabled PyTorch build using the official selector at https://pytorch.org/get-started/locally/ . Choose Windows, Pip, Python, and the CUDA version supported by your driver. Then verify:

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU')"
```

## 3. Install Stable Fast 3D

Follow the upstream installation instructions and license terms before installing model code or weights:

- Repository: https://github.com/Stability-AI/stable-fast-3d
- Model: https://huggingface.co/stabilityai/stable-fast-3d

Install its requirements into this same `.venv` environment, following the upstream instructions for your CUDA/PyTorch combination. The application adapter imports `sf3d.system.SF3D` and loads `stabilityai/stable-fast-3d`.

## 4. Run

Double-click `run_studio.bat`. Select an image and click **GENERATE 3D MODEL**. The first run can take longer while model weights download.

## Important

This is the first working application scaffold. The Stable Fast 3D adapter is an integration point and may need a small compatibility adjustment if the upstream repository changes its Python API. Model licensing and usage restrictions are governed by the upstream Stability AI license, not by this application. Do not distribute model weights with the app unless the applicable license permits it.
