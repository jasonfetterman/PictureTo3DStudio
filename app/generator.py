from __future__ import annotations

import gc
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SF3D_ROOT = PROJECT_ROOT / "external" / "stable-fast-3d"

if SF3D_ROOT.is_dir() and str(SF3D_ROOT) not in sys.path:
    sys.path.insert(0, str(SF3D_ROOT))


class GenerationError(RuntimeError):
    pass


def generate_model(
    image_path: str,
    output_path: str,
    bake_resolution: int = 512,
    progress_callback=None,
) -> str:

    image_file = Path(image_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()

    def report(message):
        if progress_callback:
            progress_callback(str(message))

    if not image_file.is_file():
        raise GenerationError(
            f"Input image does not exist:\n{image_file}"
        )

    if not SF3D_ROOT.is_dir():
        raise GenerationError(
            f"Stable Fast 3D repository not found:\n{SF3D_ROOT}"
        )

    if bake_resolution not in (512, 1024, 1536, 2048):
        raise GenerationError(
            f"Unsupported texture resolution: {bake_resolution}"
        )

    model = None
    torch = None

    try:
        report("Importing Stable Fast 3D dependencies...")

        import torch
        import rembg

        from PIL import Image
        from sf3d.system import SF3D
        from sf3d.utils import (
            remove_background,
            resize_foreground,
        )

        if not torch.cuda.is_available():
            raise GenerationError(
                "CUDA is unavailable. An NVIDIA CUDA-enabled "
                "PyTorch installation is required."
            )

        gpu_name = torch.cuda.get_device_name(0)
        gpu_properties = torch.cuda.get_device_properties(0)
        gpu_memory = gpu_properties.total_memory / (1024 ** 3)

        try:
            free_vram_bytes, _ = torch.cuda.mem_get_info(0)
            free_vram = free_vram_bytes / (1024 ** 3)
        except Exception:
            free_vram = None

        report(f"GPU: {gpu_name}")
        report(f"Total VRAM: {gpu_memory:.1f} GB")

        if free_vram is not None:
            report(f"Free VRAM: {free_vram:.2f} GB")
            if free_vram < 3.0 and bake_resolution >= 1536:
                report(
                    "WARNING: Limited free GPU memory. "
                    "Consider STANDARD / 1024 or DRAFT / 512."
                )
        else:
            report("Free VRAM: unavailable")

        report(f"PyTorch: {torch.__version__}")
        report(f"PyTorch CUDA: {torch.version.cuda}")

        report("Loading Stable Fast 3D model...")

        model = SF3D.from_pretrained(
            "stabilityai/stable-fast-3d",
            config_name="config.yaml",
            weight_name="model.safetensors",
        )

        model.to("cuda")
        model.eval()

        report("Model loaded successfully.")
        report("Removing image background...")

        rembg_session = rembg.new_session()

        with Image.open(image_file) as source:
            image = source.convert("RGBA")

        report(f"Input image: {image.width} x {image.height}")
        report(f"Texture bake resolution: {bake_resolution}")

        image = remove_background(image, rembg_session)
        image = resize_foreground(image, 0.85)

        if image.mode != "RGBA":
            image = image.convert("RGBA")

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        report("Preparing GPU inference...")

        torch.cuda.empty_cache()

        report(
            f"Generating geometry and textures "
            f"at {bake_resolution} resolution..."
        )

        # Do not apply external autocast to the complete pipeline.
        # Stable Fast 3D manages its own precision internally.
        with torch.inference_mode():
            mesh, metadata = model.run_image(
                image,
                bake_resolution=int(bake_resolution),
                remesh="none",
                vertex_count=-1,
            )

        if isinstance(mesh, list):
            if not mesh:
                raise GenerationError(
                    "Stable Fast 3D returned an empty mesh list."
                )
            mesh = mesh[0]

        if mesh is None:
            raise GenerationError(
                "Stable Fast 3D returned no mesh."
            )

        report("Exporting textured GLB...")

        mesh.export(
            str(output_file),
            include_normals=True,
        )

        if (
            not output_file.is_file()
            or output_file.stat().st_size == 0
        ):
            raise GenerationError(
                "GLB export failed or produced an empty file."
            )

        file_size = output_file.stat().st_size / (1024 * 1024)

        report(
            f"Generation complete: {output_file.name} "
            f"({file_size:.2f} MB)"
        )

        return str(output_file)

    except GenerationError:
        raise

    except Exception as exc:

        error_details = traceback.format_exc()

        if torch is not None:
            try:
                if isinstance(exc, torch.cuda.OutOfMemoryError):
                    torch.cuda.empty_cache()

                    raise GenerationError(
                        "GPU OUT OF MEMORY\n\n"
                        f"GPU: {gpu_name}\n"
                        f"VRAM: {gpu_memory:.1f} GB\n"
                        f"Texture resolution: {bake_resolution}\n\n"
                        f"Original error:\n{exc}"
                    ) from exc
            except GenerationError:
                raise
            except Exception:
                pass

        raise GenerationError(
            "STABLE FAST 3D GENERATION FAILED\n\n"
            f"Error: {type(exc).__name__}: {exc}\n\n"
            "FULL DIAGNOSTICS:\n"
            f"{error_details}"
        ) from exc

    finally:

        if model is not None:
            del model

        gc.collect()

        if torch is not None:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
