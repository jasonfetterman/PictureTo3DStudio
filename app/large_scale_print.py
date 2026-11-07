from __future__ import annotations

import json
import math
import shutil
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import trimesh

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


UNIT_TO_MM = {
    "Millimeters": 1.0,
    "Centimeters": 10.0,
    "Meters": 1000.0,
    "Inches": 25.4,
}


def load_print_mesh(source: str, source_unit: str) -> trimesh.Trimesh:
    path = Path(source)

    if not path.is_file():
        raise FileNotFoundError(f"Model not found: {path}")

    loaded = trimesh.load(
        str(path),
        force="scene",
        process=False,
    )

    if isinstance(loaded, trimesh.Scene):
        mesh = loaded.dump(concatenate=True)
    else:
        mesh = loaded

    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("The selected file did not contain a usable mesh.")

    if len(mesh.faces) == 0 or len(mesh.vertices) == 0:
        raise RuntimeError("The selected model contains no printable geometry.")

    if not np.isfinite(mesh.bounds).all():
        raise RuntimeError("The source model has invalid bounds.")

    mesh = mesh.copy()

    # STL files often duplicate vertices for every triangle.
    # Reconstruct shared topology before checking watertightness.
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()

    if not mesh.is_watertight:
        raise RuntimeError(
            "The source model is not watertight after vertex merging. "
            "Repair it before large-scale cutting."
        )

    if not mesh.is_volume:
        raise RuntimeError(
            "The source mesh is not a valid closed volume after topology repair."
        )

    mesh.vertices *= UNIT_TO_MM[source_unit]

    return mesh


def cut_cell(
    source_mesh: trimesh.Trimesh,
    lower: list[float],
    upper: list[float],
) -> trimesh.Trimesh:
    part = source_mesh.copy()

    axes = [
        ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0])
    ]

    for axis in range(3):
        normal_min = [0.0, 0.0, 0.0]
        normal_min[axis] = 1.0

        origin_min = [0.0, 0.0, 0.0]
        origin_min[axis] = lower[axis]

        part = trimesh.intersections.slice_mesh_plane(
            part,
            plane_normal=normal_min,
            plane_origin=origin_min,
            cap=True,
        )

        if part is None or len(part.faces) == 0:
            return trimesh.Trimesh()

        normal_max = [0.0, 0.0, 0.0]
        normal_max[axis] = -1.0

        origin_max = [0.0, 0.0, 0.0]
        origin_max[axis] = upper[axis]

        part = trimesh.intersections.slice_mesh_plane(
            part,
            plane_normal=normal_max,
            plane_origin=origin_max,
            cap=True,
        )

        if part is None or len(part.faces) == 0:
            return trimesh.Trimesh()

    part.remove_unreferenced_vertices()

    if len(part.faces):
        part.fix_normals()

    return part


def split_model_for_printer(
    source: str,
    output_root: str,
    target_width_mm: float,
    target_depth_mm: float,
    target_height_mm: float,
    printer_x_mm: float,
    printer_y_mm: float,
    printer_z_mm: float,
    source_unit: str = "Millimeters",
    preserve_proportions: bool = True,
    edge_clearance_mm: float = 2.0,
    progress=None,
) -> dict:
    def report(message: str):
        if progress:
            progress(message)

    target = [
        float(target_width_mm),
        float(target_depth_mm),
        float(target_height_mm),
    ]

    printer = [
        float(printer_x_mm),
        float(printer_y_mm),
        float(printer_z_mm),
    ]

    if source_unit not in UNIT_TO_MM:
        raise ValueError("Unsupported source unit.")

    if any(not math.isfinite(v) or v <= 0 for v in target + printer):
        raise ValueError("All model and printer dimensions must be positive.")

    if not math.isfinite(edge_clearance_mm) or edge_clearance_mm < 0:
        raise ValueError("Edge clearance cannot be negative.")

    usable = [v - 2.0 * edge_clearance_mm for v in printer]

    if any(v <= 0 for v in usable):
        raise ValueError("Edge clearance leaves no usable printer volume.")

    report("Loading and validating source mesh...")

    mesh = load_print_mesh(source, source_unit)

    original_extents = mesh.extents.astype(float).tolist()

    if any(not math.isfinite(v) or v <= 1e-8 for v in original_extents):
        raise RuntimeError("Source model has invalid or zero-sized dimensions.")

    if preserve_proportions:
        scale = min(
            target[i] / original_extents[i]
            for i in range(3)
        )
        factors = [scale, scale, scale]
    else:
        factors = [
            target[i] / original_extents[i]
            for i in range(3)
        ]

    mesh.vertices *= factors

    # Move the scaled model into positive X/Y/Z coordinates.
    mesh.vertices -= mesh.bounds[0]

    final_extents = mesh.extents.astype(float).tolist()

    counts = [
        max(1, math.ceil(final_extents[i] / usable[i] - 1e-10))
        for i in range(3)
    ]

    total_parts = counts[0] * counts[1] * counts[2]

    if total_parts > 300:
        raise RuntimeError(
            f"This split would create {total_parts} pieces. "
            "The current safety limit is 300 pieces."
        )

    report(
        f"Scaled model: {final_extents[0]:.2f} × "
        f"{final_extents[1]:.2f} × {final_extents[2]:.2f} mm"
    )

    report(
        f"Printer grid: {counts[0]} × {counts[1]} × {counts[2]} "
        f"({total_parts} sections)"
    )

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{Path(source).stem}_large_print_{stamp}"
    staging = root / f".staging_{folder_name}"
    destination = root / folder_name

    if staging.exists():
        shutil.rmtree(staging)

    staging.mkdir(parents=True)

    parts = []
    part_number = 0

    try:
        for iz in range(counts[2]):
            z0 = final_extents[2] * iz / counts[2]
            z1 = final_extents[2] * (iz + 1) / counts[2]

            for iy in range(counts[1]):
                y0 = final_extents[1] * iy / counts[1]
                y1 = final_extents[1] * (iy + 1) / counts[1]

                for ix in range(counts[0]):
                    x0 = final_extents[0] * ix / counts[0]
                    x1 = final_extents[0] * (ix + 1) / counts[0]

                    part_number += 1

                    report(
                        f"Cutting part {part_number}/{total_parts} "
                        f"(X{ix + 1}, Y{iy + 1}, Z{iz + 1})..."
                    )

                    part = cut_cell(
                        mesh,
                        [x0, y0, z0],
                        [x1, y1, z1],
                    )

                    if len(part.faces) == 0:
                        continue

                    if not part.is_watertight:
                        raise RuntimeError(
                            f"Part {part_number} is not watertight. "
                            "No final export was created."
                        )

                    if not part.is_volume:
                        raise RuntimeError(
                            f"Part {part_number} is not a valid closed volume."
                        )

                    dimensions = part.extents.astype(float).tolist()

                    for axis in range(3):
                        if dimensions[axis] > usable[axis] + 0.05:
                            raise RuntimeError(
                                f"Part {part_number} exceeds usable printer "
                                f"dimension on axis {axis}."
                            )

                    filename = (
                        f"PART_{part_number:03d}_"
                        f"X{ix + 1:02d}_Y{iy + 1:02d}_Z{iz + 1:02d}.stl"
                    )

                    output_file = staging / filename
                    part.export(str(output_file), file_type="stl")

                    # Reload the actual STL and validate the exported file.
                    check = trimesh.load(
                        str(output_file),
                        force="mesh",
                        process=True,
                    )

                    if not check.is_watertight or not check.is_volume:
                        raise RuntimeError(
                            f"Exported STL failed validation: {filename}"
                        )

                    parts.append({
                        "part": part_number,
                        "file": filename,
                        "grid": {
                            "x": ix + 1,
                            "y": iy + 1,
                            "z": iz + 1,
                        },
                        "position_mm": {
                            "x": round(x0, 4),
                            "y": round(y0, 4),
                            "z": round(z0, 4),
                        },
                        "dimensions_mm": [
                            round(v, 4) for v in dimensions
                        ],
                        "watertight": True,
                    })

        if not parts:
            raise RuntimeError("No printable sections were produced.")

        manifest = {
            "source_model": str(Path(source).resolve()),
            "source_unit": source_unit,
            "target_dimensions_mm": {
                "width": target_width_mm,
                "depth": target_depth_mm,
                "height": target_height_mm,
            },
            "actual_scaled_dimensions_mm": {
                "width": final_extents[0],
                "depth": final_extents[1],
                "height": final_extents[2],
            },
            "preserve_proportions": preserve_proportions,
            "printer_build_volume_mm": {
                "x": printer_x_mm,
                "y": printer_y_mm,
                "z": printer_z_mm,
            },
            "edge_clearance_mm": edge_clearance_mm,
            "usable_build_volume_mm": {
                "x": usable[0],
                "y": usable[1],
                "z": usable[2],
            },
            "grid": {
                "x": counts[0],
                "y": counts[1],
                "z": counts[2],
            },
            "part_count": len(parts),
            "assembly_note": (
                "Grid positions are measured from the lower-left-front "
                "corner of the scaled model. Dry-fit all sections before "
                "gluing. No alignment pins or sockets are included."
            ),
            "parts": parts,
        }

        with (staging / "ASSEMBLY_GUIDE.json").open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(manifest, handle, indent=2)

        if destination.exists():
            raise RuntimeError("Output folder already exists.")

        staging.rename(destination)

        report(f"Finished: {len(parts)} validated STL parts.")

        return {
            "folder": str(destination),
            "part_count": len(parts),
            "manifest": str(destination / "ASSEMBLY_GUIDE.json"),
        }

    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


from app.theme import apply_bone_white_theme

class PrintWorker(QThread):
    progress = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, **settings):
        super().__init__()
        self.settings = settings

    def run(self):
        try:
            result = split_model_for_printer(
                **self.settings,
                progress=self.progress.emit,
            )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(
                f"{exc}\n\n{traceback.format_exc()}"
            )


class LargeScalePrintWindow(QDialog):
    def __init__(self, model_path: str | None = None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Large-Scale Print Studio")
        self.resize(650, 760)
        apply_bone_white_theme(self)

        self.model_path = model_path
        self.worker = None

        root = QVBoxLayout(self)

        heading = QLabel("LARGE-SCALE PRINT STUDIO")
        heading.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #8A5A3C;"
        )
        root.addWidget(heading)

        description = QLabel(
            "Scale a model to your desired size, divide it into printer-sized "
            "sections, and export numbered STL files with an assembly guide."
        )
        description.setWordWrap(True)
        root.addWidget(description)

        source_group = QGroupBox("01 / SOURCE MODEL")
        source_layout = QVBoxLayout(source_group)

        self.source_label = QLabel()
        self.source_label.setWordWrap(True)
        self.update_source_label()

        browse = QPushButton("CHOOSE MODEL")
        browse.clicked.connect(self.choose_model)

        source_layout.addWidget(self.source_label)
        source_layout.addWidget(browse)
        root.addWidget(source_group)

        target_group = QGroupBox("02 / FINAL MODEL SIZE (MM)")
        target_form = QFormLayout(target_group)

        self.width_box = self.dimension_box(200)
        self.depth_box = self.dimension_box(200)
        self.height_box = self.dimension_box(200)

        target_form.addRow("Width (X):", self.width_box)
        target_form.addRow("Depth (Y):", self.depth_box)
        target_form.addRow("Height (Z):", self.height_box)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(list(UNIT_TO_MM.keys()))
        target_form.addRow("Source model units:", self.unit_combo)

        self.proportions = QCheckBox("Preserve original proportions")
        self.proportions.setChecked(True)
        target_form.addRow(self.proportions)

        root.addWidget(target_group)

        printer_group = QGroupBox("03 / YOUR PRINTER BUILD VOLUME (MM)")
        printer_form = QFormLayout(printer_group)

        self.printer_x = self.dimension_box(220)
        self.printer_y = self.dimension_box(220)
        self.printer_z = self.dimension_box(250)
        self.clearance = self.dimension_box(2, maximum=20)

        printer_form.addRow("Printer X:", self.printer_x)
        printer_form.addRow("Printer Y:", self.printer_y)
        printer_form.addRow("Printer Z:", self.printer_z)
        printer_form.addRow("Edge clearance:", self.clearance)

        root.addWidget(printer_group)

        self.estimate = QLabel(
            "Enter your dimensions to calculate the required sections."
        )
        self.estimate.setWordWrap(True)
        root.addWidget(self.estimate)

        self.progress_label = QLabel("Ready.")
        self.progress_label.setWordWrap(True)
        root.addWidget(self.progress_label)

        buttons = QHBoxLayout()

        self.calculate_button = QPushButton("CALCULATE SECTIONS")
        self.calculate_button.clicked.connect(self.calculate_sections)

        self.split_button = QPushButton("SPLIT AND EXPORT STL PIECES")
        self.split_button.clicked.connect(self.start_split)

        close_button = QPushButton("CLOSE")
        close_button.clicked.connect(self.close)

        buttons.addWidget(self.calculate_button)
        buttons.addWidget(self.split_button)
        buttons.addWidget(close_button)

        root.addLayout(buttons)

    @staticmethod
    def dimension_box(value: float, maximum: float = 100000.0):
        box = QDoubleSpinBox()
        box.setRange(0.01, maximum)
        box.setDecimals(2)
        box.setSingleStep(10.0)
        box.setValue(value)
        box.setSuffix(" mm")
        return box

    def update_source_label(self):
        self.source_label.setText(
            self.model_path if self.model_path else "No model selected."
        )

    def choose_model(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a 3D model",
            "",
            "3D Models (*.glb *.gltf *.obj *.stl *.ply *.3mf);;All Files (*.*)",
        )

        if filename:
            self.model_path = filename
            self.update_source_label()

    def current_settings(self):
        if not self.model_path:
            raise ValueError("Choose a model first.")

        return {
            "source": self.model_path,
            "output_root": str(
                Path(__file__).resolve().parents[1]
                / "output"
                / "large_scale_print"
            ),
            "target_width_mm": self.width_box.value(),
            "target_depth_mm": self.depth_box.value(),
            "target_height_mm": self.height_box.value(),
            "printer_x_mm": self.printer_x.value(),
            "printer_y_mm": self.printer_y.value(),
            "printer_z_mm": self.printer_z.value(),
            "source_unit": self.unit_combo.currentText(),
            "preserve_proportions": self.proportions.isChecked(),
            "edge_clearance_mm": self.clearance.value(),
        }

    def calculate_sections(self):
        try:
            settings = self.current_settings()
            mesh = load_print_mesh(
                settings["source"],
                settings["source_unit"],
            )

            extents = mesh.extents.astype(float).tolist()
            target = [
                settings["target_width_mm"],
                settings["target_depth_mm"],
                settings["target_height_mm"],
            ]

            if self.proportions.isChecked():
                scale = min(target[i] / extents[i] for i in range(3))
                actual = [v * scale for v in extents]
            else:
                actual = target

            usable = [
                settings["printer_x_mm"] - 2 * settings["edge_clearance_mm"],
                settings["printer_y_mm"] - 2 * settings["edge_clearance_mm"],
                settings["printer_z_mm"] - 2 * settings["edge_clearance_mm"],
            ]

            if any(v <= 0 for v in usable):
                raise ValueError("Printer clearance leaves no usable volume.")

            counts = [
                max(1, math.ceil(actual[i] / usable[i] - 1e-10))
                for i in range(3)
            ]

            total = counts[0] * counts[1] * counts[2]

            self.estimate.setText(
                f"Estimated final size: "
                f"{actual[0]:.2f} × {actual[1]:.2f} × "
                f"{actual[2]:.2f} mm\n"
                f"Cut grid: {counts[0]} × {counts[1]} × {counts[2]}\n"
                f"Estimated maximum sections: {total}"
            )

            self.progress_label.setText("Dimensions calculated.")

        except Exception as exc:
            QMessageBox.warning(self, "Cannot calculate", str(exc))

    def set_controls_enabled(self, enabled: bool):
        for control in (
            self.calculate_button,
            self.split_button,
        ):
            control.setEnabled(enabled)

    def start_split(self):
        try:
            settings = self.current_settings()
        except Exception as exc:
            QMessageBox.warning(self, "Missing information", str(exc))
            return

        answer = QMessageBox.question(
            self,
            "Confirm large-scale split",
            "The original model will not be modified.\n\n"
            "The application will create a new folder containing "
            "numbered STL pieces and an assembly guide.\n\n"
            "Continue?",
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.set_controls_enabled(False)
        self.progress_label.setText("Starting mesh processing...")

        self.worker = PrintWorker(**settings)
        self.worker.progress.connect(self.progress_label.setText)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_completed(self, result):
        self.progress_label.setText(
            f"Export complete: {result['part_count']} validated parts."
        )

        QMessageBox.information(
            self,
            "Large-scale export complete",
            f"Created {result['part_count']} STL pieces.\n\n"
            f"Output folder:\n{result['folder']}\n\n"
            f"Assembly guide:\n{result['manifest']}",
        )

    def on_failed(self, message):
        self.progress_label.setText("Export failed.")
        QMessageBox.critical(
            self,
            "Large-scale export failed",
            message,
        )

    def on_worker_finished(self):
        self.set_controls_enabled(True)
        self.worker = None

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(
                self,
                "Processing in progress",
                "Wait for the current export to finish before closing.",
            )
            event.ignore()
            return

        event.accept()
