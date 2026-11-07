
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

import numpy as np
import trimesh


BLENDER_EXE = Path(
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)


BLENDER_SCRIPT = r'''
import bpy
import sys
import traceback
from pathlib import Path


def log(message):
    print("[PICTURE3D] " + str(message))


def import_model(source):
    suffix = Path(source).suffix.lower()

    if suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=source)
    elif suffix in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=source)
    elif suffix == ".stl":
        bpy.ops.wm.stl_import(filepath=source)
    elif suffix == ".ply":
        bpy.ops.wm.ply_import(filepath=source)
    elif suffix == ".3mf":
        bpy.ops.import_mesh.threemf(filepath=source)
    else:
        raise RuntimeError("Unsupported model format: " + suffix)


def get_meshes():
    return [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH"
    ]


def export_obj(path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.wm.obj_export(
        filepath=path,
        export_selected_objects=True,
        export_triangulated_mesh=False,
        export_uv=True,
        export_normals=True,
        export_materials=True,
        apply_modifiers=True
    )


def export_glb(path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_apply=True
    )


def remesh_individually(objects, target_faces):
    successful = 0

    for obj in list(objects):
        if obj.name not in bpy.data.objects:
            continue

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        original_name = obj.name
        original_materials = [
            slot.material for slot in obj.material_slots
        ]

        original_dimensions = tuple(obj.dimensions)

        log("Remeshing object: " + original_name)

        bpy.ops.object.quadriflow_remesh(
            target_faces=target_faces,
            use_preserve_sharp=True,
            use_preserve_boundary=True
        )

        result = bpy.context.view_layer.objects.active

        if result is None or result.type != "MESH":
            raise RuntimeError(
                "Remeshing failed for object: " + original_name
            )

        if len(result.data.polygons) == 0:
            raise RuntimeError(
                "Remeshing produced empty geometry: " + original_name
            )

        # Restore material slots when Quadriflow drops them.
        if len(result.data.materials) == 0:
            for material in original_materials:
                result.data.materials.append(material)

        result.name = original_name
        successful += 1

        log(
            "Remeshed "
            + original_name
            + " | faces: "
            + str(len(result.data.polygons))
        )

    if successful == 0:
        raise RuntimeError("No objects were remeshed.")

    return successful


def main():
    args = sys.argv[sys.argv.index("--") + 1:]

    source = str(Path(args[0]).resolve())
    output = str(Path(args[1]).resolve())
    mode = args[2].upper()
    target_faces = max(500, int(args[3]))

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    log("Importing: " + source)
    import_model(source)

    meshes = get_meshes()

    if not meshes:
        raise RuntimeError("No mesh geometry was imported.")

    log("Imported separate mesh objects: " + str(len(meshes)))

    # Do not join objects. Preserve separate parts and materials.
    if mode == "QUAD":
        remesh_individually(meshes, target_faces)
        export_obj(output)

    elif mode == "TRI":
        # Do not unnecessarily modify source geometry.
        # Triangulate copies of each object's mesh data.
        for obj in meshes:
            obj.data = obj.data.copy()

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.quads_convert_to_tris(
                quad_method="BEAUTY"
            )
            bpy.ops.object.mode_set(mode="OBJECT")

        if output.lower().endswith(".obj"):
            export_obj(output)
        else:
            export_glb(output)

    else:
        raise RuntimeError("Unknown topology mode: " + mode)

    result = Path(output)

    if not result.is_file() or result.stat().st_size == 0:
        raise RuntimeError("Export failed or produced an empty file.")

    log("TOPOLOGY_EXPORT_SUCCESS")
    log("Output: " + output)


try:
    main()
except Exception:
    traceback.print_exc()
    raise
'''


def run_topology(
    source_path,
    output_path,
    mode,
    target_faces=5000,
):
    source_path = Path(source_path).resolve()
    output_path = Path(output_path).resolve()
    mode = str(mode).upper()

    if not BLENDER_EXE.is_file():
        raise RuntimeError(
            f"Blender executable not found:\n{BLENDER_EXE}"
        )

    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    if mode not in ("QUAD", "TRI"):
        raise ValueError("Mode must be QUAD or TRI.")

    if mode == "QUAD" and output_path.suffix.lower() != ".obj":
        raise ValueError("Quad output must use OBJ format.")

    if mode == "TRI" and output_path.suffix.lower() != ".glb":
        raise ValueError("Triangle output must use GLB format.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="picture3d_"
    ) as temp_dir:

        script = Path(temp_dir) / "topology.py"
        script.write_text(BLENDER_SCRIPT, encoding="utf-8")

        command = [
            str(BLENDER_EXE),
            "--background",
            "--python",
            str(script),
            "--",
            str(source_path),
            str(output_path),
            mode,
            str(max(500, int(target_faces))),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=900,
            errors="replace",
        )

        output_log = (
            (result.stdout or "")
            + "\n"
            + (result.stderr or "")
        )

        print(output_log)

        if result.returncode != 0:
            raise RuntimeError(
                "Blender processing failed:\n" + output_log[-10000:]
            )

        if "TOPOLOGY_EXPORT_SUCCESS" not in output_log:
            raise RuntimeError(
                "Blender did not confirm successful export."
            )

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("Output file is missing or empty.")

    return str(output_path)


def scan_mesh(source_path):
    source_path = Path(source_path)

    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    loaded = trimesh.load(
        str(source_path),
        force="scene",
        process=False,
    )

    if isinstance(loaded, trimesh.Scene):
        mesh = loaded.dump(concatenate=True)
    else:
        mesh = loaded

    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("No usable mesh geometry found.")

    if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise RuntimeError("Model contains no usable geometry.")

    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)

    if not np.isfinite(vertices).all():
        raise RuntimeError("Model contains invalid vertex coordinates.")

    edge_usage = np.bincount(
        mesh.edges_unique_inverse,
        minlength=len(mesh.edges_unique),
    )

    boundary_edges = int(np.count_nonzero(edge_usage == 1))
    nonmanifold_edges = int(np.count_nonzero(edge_usage > 2))
    degenerate_faces = int(
        np.count_nonzero(mesh.area_faces <= 1e-12)
    )

    components = mesh.split(only_watertight=False)
    component_sizes = sorted(
        [len(part.faces) for part in components],
        reverse=True,
    )

    adjacency_angles = np.asarray(mesh.face_adjacency_angles)
    sharp_edges = int(
        np.count_nonzero(adjacency_angles > np.deg2rad(35))
    )

    complexity_ratio = sharp_edges / max(len(faces), 1)

    if complexity_ratio > 0.20:
        recommendation = "HIGH detail"
        suggested_faces = min(100000, max(5000, len(faces) * 2))
    elif complexity_ratio > 0.07:
        recommendation = "MEDIUM detail"
        suggested_faces = min(100000, max(3000, len(faces)))
    else:
        recommendation = "LOWER detail"
        suggested_faces = min(
            100000,
            max(1500, int(len(faces) * 0.75)),
        )

    dimensions = mesh.extents

    uv = getattr(mesh.visual, "uv", None)
    has_uv = uv is not None

    return "\n".join([
        "MESH SCAN REPORT",
        "--------------------------------",
        f"File: {source_path.name}",
        f"Vertices: {len(vertices):,}",
        f"Faces: {len(faces):,}",
        f"Surface area: {mesh.area:.4f}",
        (
            f"Dimensions: {dimensions[0]:.4f} x "
            f"{dimensions[1]:.4f} x {dimensions[2]:.4f}"
        ),
        f"Watertight: {mesh.is_watertight}",
        f"Consistent normals: {mesh.is_winding_consistent}",
        f"Boundary edges: {boundary_edges:,}",
        f"Non-manifold edges: {nonmanifold_edges:,}",
        f"Degenerate faces: {degenerate_faces:,}",
        f"Disconnected components: {len(components):,}",
        f"Largest component faces: {component_sizes[0]:,}",
        f"UV coordinates present: {has_uv}",
        f"Sharp surface transitions: {sharp_edges:,}",
        "",
        "ADAPTIVE DETAIL RECOMMENDATION",
        recommendation,
        f"Suggested starting face target: {suggested_faces:,}",
        "",
        "Source geometry is analyzed without modification.",
    ])
