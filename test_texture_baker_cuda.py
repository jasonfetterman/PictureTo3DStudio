import sys
import torch

sys.path.insert(0, r"C:\PictureTo3DStudio_MVP\PictureTo3DStudio\external\stable-fast-3d\texture_baker")

print("PyTorch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("GPU:", torch.cuda.get_device_name(0))

import texture_baker
from texture_baker import TextureBaker

print("Package loaded from:", texture_baker.__file__)
print("Native extension:", texture_baker._C.__file__)

baker = TextureBaker()

uv = torch.tensor(
    [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
    dtype=torch.float32,
    device="cuda"
).contiguous()

faces = torch.tensor(
    [[0, 1, 2]],
    dtype=torch.int64,
    device="cuda"
).contiguous()

print("\n--- CUDA RASTERIZE TEST ---")
rast = baker.rasterize(uv, faces, 64)
torch.cuda.synchronize()

print("Raster device:", rast.device)
print("Raster shape:", tuple(rast.shape))
print("Raster dtype:", rast.dtype)
print("Raster finite:", torch.isfinite(rast).all().item())

assert rast.is_cuda
assert tuple(rast.shape) == (64, 64, 4)

print("\n--- CUDA INTERPOLATE TEST ---")
attr = torch.tensor(
    [[1.0, 0.0, 0.0],
     [0.0, 1.0, 0.0],
     [0.0, 0.0, 1.0]],
    dtype=torch.float32,
    device="cuda"
).contiguous()

out = baker.interpolate(attr, rast, faces)
torch.cuda.synchronize()

print("Interpolated device:", out.device)
print("Interpolated shape:", tuple(out.shape))
print("Interpolated dtype:", out.dtype)
print("Interpolated finite:", torch.isfinite(out).all().item())

assert out.is_cuda
assert tuple(out.shape) == (64, 64, 3)

print("\nSUCCESS: Both texture baker CUDA kernels executed.")
