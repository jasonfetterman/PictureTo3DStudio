import os
from pathlib import Path

import torch
from setuptools import find_packages, setup
from torch.utils.cpp_extension import CUDA_HOME, BuildExtension, CUDAExtension

ROOT = Path(__file__).resolve().parent
PACKAGE = "texture_baker"
SOURCE_DIR = ROOT / PACKAGE / "csrc"

if os.name != "nt":
    raise RuntimeError("This build configuration is intended for Windows.")

if CUDA_HOME is None:
    raise RuntimeError(
        "CUDA was explicitly requested, but PyTorch could not locate CUDA_HOME."
    )

if torch.version.cuda is None:
    raise RuntimeError(
        "The installed PyTorch build does not include CUDA support."
    )

if not torch.cuda.is_available():
    raise RuntimeError(
        "PyTorch cannot access the CUDA GPU. Refusing to build a CPU-only extension."
    )

cpp_sources = sorted(str(path) for path in SOURCE_DIR.glob("*.cpp"))
cuda_sources = sorted(str(path) for path in SOURCE_DIR.glob("*.cu"))

if not cpp_sources:
    raise RuntimeError(f"No C++ sources found in {SOURCE_DIR}")

if not cuda_sources:
    raise RuntimeError(f"No CUDA sources found in {SOURCE_DIR}")

sources = cpp_sources + cuda_sources

print("\n========== TEXTURE BAKER CUDA BUILD ==========")
print("Package:", PACKAGE)
print("CUDA_HOME:", CUDA_HOME)
print("PyTorch:", torch.__version__)
print("PyTorch CUDA:", torch.version.cuda)
print("GPU:", torch.cuda.get_device_name(0))
print("Architecture:", os.environ.get("TORCH_CUDA_ARCH_LIST", "PyTorch default"))
print("C++ sources:", cpp_sources)
print("CUDA sources:", cuda_sources)
print("CPU-only fallback: DISABLED")

extension = CUDAExtension(
    name=f"{PACKAGE}._C",
    sources=sources,
    define_macros=[
        ("THRUST_IGNORE_CUB_VERSION_CHECK", None),
    ],
    extra_compile_args={
        "cxx": [
            "/O2",
            "/std:c++17",
        ],
        "nvcc": [
            "-O3",
            "-std=c++17",
        ],
    },
    libraries=[
        "cudart",
        "c10_cuda",
        "c10",
        "torch",
        "torch_cpu",
        "torch_python",
    ],
)

setup(
    name=PACKAGE,
    version="0.0.1",
    packages=find_packages(where="."),
    package_dir={"": "."},
    ext_modules=[extension],
    install_requires=[],
    package_data={
        PACKAGE: [
            os.path.join("csrc", "*.h"),
            os.path.join("csrc", "*.metal"),
        ],
    },
    description="CUDA-enabled texture baker.",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/Stability-AI/texture_baker",
    cmdclass={
        "build_ext": BuildExtension.with_options(use_ninja=False),
    },
)
