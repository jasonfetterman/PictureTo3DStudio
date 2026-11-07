import torch
import texture_baker
from texture_baker import TextureBaker

print("PyTorch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("GPU:", torch.cuda.get_device_name(0))
print("Package:", texture_baker.__file__)
print("Extension:", texture_baker._C.__file__)

assert ".venv" in texture_baker._C.__file__, "Unexpected extension location"

baker = TextureBaker()

uv = torch.tensor(
    [[0., 0.], [1., 0.], [0., 1.]],
    device="cuda", dtype=torch.float32
)

faces = torch.tensor(
    [[0, 1, 2]],
    device="cuda", dtype=torch.int64
)

rast = baker.rasterize(uv, faces, 64)
torch.cuda.synchronize()

attr = torch.tensor(
    [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]],
    device="cuda", dtype=torch.float32
)

out = baker.interpolate(attr, rast, faces)
torch.cuda.synchronize()

print("Raster:", rast.device, tuple(rast.shape))
print("Interpolation:", out.device, tuple(out.shape))
print("Installed CUDA extension test PASSED.")
