import os
from pathlib import Path

from app.generator import generate_model

image = Path(os.environ["SF3D_TEST_IMAGE"])
output = Path("output") / "sf3d_smoke_test.glb"

print("STARTING REAL STABLE FAST 3D GENERATION", flush=True)
print(f"Input: {image}", flush=True)

result = generate_model(
    image_path=str(image),
    output_path=str(output),
    bake_resolution=512,
    progress_callback=lambda message: print(f"[SF3D] {message}", flush=True),
)

result_path = Path(result)

print("\nGENERATION SUCCESSFUL", flush=True)
print(f"Output: {result_path.resolve()}", flush=True)
print(f"File size: {result_path.stat().st_size:,} bytes", flush=True)
