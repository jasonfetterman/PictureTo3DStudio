
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

import trimesh

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QProgressBar,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QTextEdit,
    QMessageBox,
    QSplitter,
    QSizePolicy,
)

from app.blender_mesh import BLENDER_EXE, run_topology, scan_mesh
from app.converter import ConversionCenter
from app.text_to_image import TextToImageWindow
from app.large_scale_print import LargeScalePrintWindow


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

SUPPORTED_FORMATS = {
    ".glb",
    ".gltf",
    ".obj",
    ".stl",
    ".ply",
    ".3mf",
}

IMAGE_FILTER = (
    "Image files (*.png *.jpg *.jpeg *.webp *.bmp);;"
    "All files (*.*)"
)

MODEL_FILTER = (
    "3D models (*.glb *.gltf *.obj *.stl *.ply *.3mf);;"
    "All files (*.*)"
)

EXPORT_FILTER = (
    "GLB model (*.glb);;"
    "GLTF model (*.gltf);;"
    "OBJ model (*.obj);;"
    "STL model (*.stl);;"
    "PLY model (*.ply);;"
    "3MF model (*.3mf)"
)


# ---------------------------------------------------------------------
# Blender native model viewer
# ---------------------------------------------------------------------

BLENDER_VIEW_SCRIPT = r'''
import bpy
import sys
import traceback
from pathlib import Path


def log(message):
    print("[PICTURE3D VIEWER] " + str(message))


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
        # Blender installations differ in 3MF support.
        # Try the available import operator.
        if hasattr(bpy.ops.import_mesh, "threemf"):
            bpy.ops.import_mesh.threemf(filepath=source)
        else:
            raise RuntimeError(
                "This Blender installation does not have a 3MF importer."
            )

    else:
        raise RuntimeError("Unsupported model format: " + suffix)


def frame_model(objects):
    bpy.ops.object.select_all(action="DESELECT")

    for obj in objects:
        if obj.name in bpy.data.objects:
            obj.select_set(True)

    if objects:
        bpy.context.view_layer.objects.active = objects[0]

    # Frame the imported model in the 3D viewport.
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue

            space = area.spaces.active
            space.shading.type = "MATERIAL"

            for region in area.regions:
                if region.type == "WINDOW":
                    try:
                        with bpy.context.temp_override(
                            window=window,
                            area=area,
                            region=region,
                        ):
                            bpy.ops.view3d.view_selected(
                                use_all_regions=False
                            )
                    except Exception as exc:
                        log("Viewport framing warning: " + str(exc))

            space.overlay.show_floor = True
            space.overlay.show_axis_x = True
            space.overlay.show_axis_y = True


def main():
    if "--" not in sys.argv:
        raise RuntimeError("No model path was provided to Blender.")

    args = sys.argv[sys.argv.index("--") + 1:]

    if not args:
        raise RuntimeError("No model path was provided to Blender.")

    source = str(Path(args[0]).resolve())

    if not Path(source).is_file():
        raise FileNotFoundError(source)

    # Remove startup scene objects.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    log("Importing original model: " + source)

    import_model(source)

    imported = [
        obj for obj in bpy.context.scene.objects
        if obj.type in ("MESH", "CURVE", "SURFACE", "FONT")
    ]

    if not imported:
        raise RuntimeError("The file imported, but no visible model objects were found.")

    frame_model(imported)

    log("Imported objects: " + str(len(imported)))
    log("Model opened successfully.")


try:
    main()
except Exception:
    traceback.print_exc()
    raise
'''


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def unique_output_path(path: Path) -> Path:
    """Return a path that will not overwrite an existing file."""
    path = Path(path)

    if not path.exists():
        return path

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(
        f"{path.stem}_{stamp}{path.suffix}"
    )

    counter = 1

    while candidate.exists():
        candidate = path.with_name(
            f"{path.stem}_{stamp}_{counter}{path.suffix}"
        )
        counter += 1

    return candidate


def inspect_model(path: str) -> tuple[int, int]:
    """Read mesh statistics without modifying or exporting the source."""
    loaded = trimesh.load(
        path,
        force="scene",
        process=False,
    )

    if isinstance(loaded, trimesh.Scene):
        geometries = [
            geometry
            for geometry in loaded.geometry.values()
            if isinstance(geometry, trimesh.Trimesh)
        ]
    elif isinstance(loaded, trimesh.Trimesh):
        geometries = [loaded]
    else:
        geometries = []

    if not geometries:
        raise RuntimeError("No usable mesh geometry was found.")

    vertices = sum(len(mesh.vertices) for mesh in geometries)
    faces = sum(len(mesh.faces) for mesh in geometries)

    if vertices == 0 or faces == 0:
        raise RuntimeError("The model contains no usable geometry.")

    return vertices, faces


def export_model(source: str, destination: str) -> str:
    """Export a model using trimesh without changing the original file."""
    source_path = Path(source)
    destination_path = Path(destination)

    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    if destination_path.resolve() == source_path.resolve():
        raise RuntimeError("Export destination cannot overwrite the source model.")

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    loaded = trimesh.load(
        str(source_path),
        force="scene",
        process=False,
    )

    if not isinstance(loaded, (trimesh.Scene, trimesh.Trimesh)):
        raise RuntimeError("The source file does not contain a supported mesh.")

    loaded.export(str(destination_path))

    if not destination_path.is_file() or destination_path.stat().st_size == 0:
        raise RuntimeError(
            "Export did not produce a valid output file. "
            "The selected format may require an additional exporter."
        )

    return str(destination_path)


# ---------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------

from app.theme import apply_bone_white_theme

class Worker(QThread):
    progress = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        task: str,
        **kwargs,
    ):
        super().__init__()
        self.task = task
        self.kwargs = kwargs

    def run(self):
        try:
            if self.task == "generate":
                from app.generator import generate_model

                result = generate_model(
                    self.kwargs["image_path"],
                    self.kwargs["output_path"],
                    self.kwargs["resolution"],
                    self.progress.emit,
                )

                self.completed.emit(result)

            elif self.task == "scan":
                result = scan_mesh(self.kwargs["model_path"])
                self.completed.emit(result)

            elif self.task == "topology":
                result = run_topology(
                    self.kwargs["source"],
                    self.kwargs["output"],
                    self.kwargs["mode"],
                    self.kwargs["target_faces"],
                )
                self.completed.emit(result)

            elif self.task == "export":
                result = export_model(
                    self.kwargs["source"],
                    self.kwargs["destination"],
                )
                self.completed.emit(result)

            else:
                raise RuntimeError(
                    f"Unknown background task: {self.task}"
                )

        except Exception as exc:
            self.failed.emit(
                f"{exc}\n\n{traceback.format_exc()}"
            )


# ---------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------

class Studio(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Picture-to-3D Model Studio")
        self.resize(1450, 900)
        self.setMinimumSize(1050, 700)

        self.image_path: str | None = None
        self.model_path: str | None = None
        self.quad_model_path: str | None = None
        self.worker: Worker | None = None
        self.print_window = None

        self.build_ui()
        self.apply_style()

        self.statusBar().showMessage(
            "Ready · Import an image to begin"
        )

    # -----------------------------------------------------------------
    # Interface construction
    # -----------------------------------------------------------------

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 16, 18, 14)
        root_layout.setSpacing(12)

        # Header
        header = QHBoxLayout()

        title_column = QVBoxLayout()

        title = QLabel("PICTURE-TO-3D MODEL STUDIO")
        title.setObjectName("mainTitle")

        subtitle = QLabel(
            "IMAGE GENERATION  /  TEXTURED GEOMETRY  /  MODEL PROCESSING"
        )
        subtitle.setObjectName("subtitle")

        title_column.addWidget(title)
        title_column.addWidget(subtitle)

        header.addLayout(title_column)
        header.addStretch()

        self.engine_badge = QLabel("AI ENGINE  ·  STABLE FAST 3D")
        self.engine_badge.setObjectName("engineBadge")
        header.addWidget(self.engine_badge)

        root_layout.addLayout(header)

        # Main horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_panel = self.build_left_panel()
        right_panel = self.build_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([470, 900])

        root_layout.addWidget(splitter, 1)

    def build_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)

        # Image input
        image_group = QGroupBox("01  /  SOURCE IMAGE")
        image_layout = QVBoxLayout(image_group)

        self.image_preview = QLabel("NO SOURCE IMAGE SELECTED")
        self.image_preview.setObjectName("imagePreview")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumHeight(190)
        self.image_preview.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        image_layout.addWidget(self.image_preview)

        self.text_to_image_btn = QPushButton("CREATE IMAGE FROM TEXT")
        self.text_to_image_btn.setObjectName("primaryButton")
        self.text_to_image_btn.setMinimumHeight(40)
        self.text_to_image_btn.clicked.connect(self.open_text_to_image)
        image_layout.addWidget(self.text_to_image_btn)

        image_buttons = QHBoxLayout()

        self.choose_image_btn = QPushButton("CHOOSE IMAGE")
        self.choose_image_btn.clicked.connect(self.choose_image)

        self.clear_image_btn = QPushButton("CLEAR")
        self.clear_image_btn.setObjectName("secondaryButton")
        self.clear_image_btn.clicked.connect(self.clear_image)

        image_buttons.addWidget(self.choose_image_btn)
        image_buttons.addWidget(self.clear_image_btn)

        image_layout.addLayout(image_buttons)
        layout.addWidget(image_group)

        # Generation settings
        generation_group = QGroupBox("02  /  AI MODEL GENERATION")
        generation_layout = QVBoxLayout(generation_group)

        engine_info = QLabel(
            "STABLE FAST 3D\n"
            "Single-image to textured 3D geometry\n"
            "CUDA-enabled NVIDIA GPU required"
        )
        engine_info.setObjectName("infoText")
        generation_layout.addWidget(engine_info)

        resolution_row = QHBoxLayout()

        resolution_label = QLabel("Generation quality")

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("DRAFT  /  512", 512)
        self.resolution_combo.addItem("STANDARD  /  1024", 1024)
        self.resolution_combo.addItem("HIGH QUALITY  /  1536", 1536)
        self.resolution_combo.addItem("ULTRA  /  2048", 2048)
        self.resolution_combo.setCurrentIndex(1)

        resolution_row.addWidget(resolution_label)
        resolution_row.addStretch()
        resolution_row.addWidget(self.resolution_combo)

        generation_layout.addLayout(resolution_row)

        self.generate_btn = QPushButton("GENERATE 3D MODEL")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.clicked.connect(self.generate_model)

        generation_layout.addWidget(self.generate_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)

        generation_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel(
            "Waiting for source image."
        )
        self.progress_label.setObjectName("mutedText")
        self.progress_label.setWordWrap(True)

        generation_layout.addWidget(self.progress_label)

        layout.addWidget(generation_group)

        # Existing model
        existing_group = QGroupBox("03  /  EXISTING MODEL")
        existing_layout = QVBoxLayout(existing_group)

        self.model_label = QLabel("No model loaded")
        self.model_label.setObjectName("infoText")
        self.model_label.setWordWrap(True)

        existing_layout.addWidget(self.model_label)

        self.open_model_btn = QPushButton("OPEN EXISTING MODEL")
        self.open_model_btn.clicked.connect(self.open_existing_model)

        existing_layout.addWidget(self.open_model_btn)

        self.print_studio_btn = QPushButton("LARGE-SCALE PRINT STUDIO")
        self.print_studio_btn.setObjectName("primaryButton")
        self.print_studio_btn.clicked.connect(self.open_large_scale_print)
        existing_layout.addWidget(self.print_studio_btn)

        layout.addWidget(existing_group)

        # Mesh processing
        topology_group = QGroupBox("04  /  MESH PROCESSING")
        topology_layout = QVBoxLayout(topology_group)

        target_row = QHBoxLayout()

        target_row.addWidget(QLabel("Quad target faces"))

        self.quad_target = QSpinBox()
        self.quad_target.setRange(500, 100000)
        self.quad_target.setSingleStep(500)
        self.quad_target.setValue(5000)

        target_row.addWidget(self.quad_target)

        topology_layout.addLayout(target_row)

        self.scan_btn = QPushButton("SCAN MESH")
        self.scan_btn.clicked.connect(self.scan_current_model)

        self.quad_btn = QPushButton("GENERATE QUAD MESH")
        self.quad_btn.clicked.connect(self.generate_quad_mesh)

        self.tri_btn = QPushButton("CONVERT TO TRIANGLES")
        self.tri_btn.clicked.connect(self.generate_triangle_mesh)

        topology_layout.addWidget(self.scan_btn)
        topology_layout.addWidget(self.quad_btn)
        topology_layout.addWidget(self.tri_btn)

        layout.addWidget(topology_group)

        layout.addStretch()

        return panel

    def build_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(12)

        # Blender viewport area
        viewer_frame = QFrame()
        viewer_frame.setObjectName("viewerFrame")

        viewer_layout = QVBoxLayout(viewer_frame)
        viewer_layout.setContentsMargins(24, 22, 24, 22)
        viewer_layout.setSpacing(16)

        viewer_header = QHBoxLayout()

        viewer_title_column = QVBoxLayout()

        viewer_title = QLabel("3D MODEL VIEWPORT")
        viewer_title.setObjectName("viewerTitle")

        viewer_subtitle = QLabel(
            "BLENDER NATIVE RENDERING  /  ORIGINAL MODEL GEOMETRY"
        )
        viewer_subtitle.setObjectName("viewerSubtitle")

        viewer_title_column.addWidget(viewer_title)
        viewer_title_column.addWidget(viewer_subtitle)

        viewer_header.addLayout(viewer_title_column)
        viewer_header.addStretch()

        self.blender_status = QLabel("BLENDER VIEWPORT READY")
        self.blender_status.setObjectName("statusBadge")

        viewer_header.addWidget(self.blender_status)

        viewer_layout.addLayout(viewer_header)

        viewer_layout.addStretch()

        self.viewer_message = QLabel(
            "NO MODEL LOADED\n\n"
            "Generate a model from an image or open an existing model.\n\n"
            "The model will be imported directly into Blender.\n"
            "Its original geometry, materials, UVs and textures are preserved."
        )
        self.viewer_message.setObjectName("viewerMessage")
        self.viewer_message.setAlignment(Qt.AlignCenter)
        self.viewer_message.setWordWrap(True)

        viewer_layout.addWidget(self.viewer_message)

        viewer_layout.addStretch()

        self.maya_btn = QPushButton("OPEN MODEL IN MAYA")
        self.maya_btn.setObjectName("primaryButton")
        self.maya_btn.clicked.connect(self.open_in_maya)
        self.maya_btn.setEnabled(True)
        viewer_layout.addWidget(self.maya_btn)

        viewer_buttons = QHBoxLayout()

        self.blender_btn = QPushButton("OPEN MODEL IN BLENDER")
        self.blender_btn.setObjectName("primaryButton")
        self.blender_btn.clicked.connect(self.open_in_blender)
        self.blender_btn.setEnabled(False)

        self.export_btn = QPushButton("EXPORT MODEL")
        self.export_btn.clicked.connect(self.export_current_model)
        self.export_btn.setEnabled(False)

        viewer_buttons.addWidget(self.blender_btn)
        viewer_buttons.addWidget(self.export_btn)

        viewer_layout.addLayout(viewer_buttons)

        self.convert_btn = QPushButton("OPEN MODEL CONVERSION CENTER")
        self.convert_btn.setObjectName("primaryButton")
        self.convert_btn.clicked.connect(self.open_conversion_center)
        viewer_layout.addWidget(self.convert_btn)

        layout.addWidget(viewer_frame, 3)

        # Model information
        information_group = QGroupBox("MODEL INFORMATION")
        information_layout = QGridLayout(information_group)

        self.info_file = QLabel("No model")
        self.info_vertices = QLabel("—")
        self.info_faces = QLabel("—")
        self.info_format = QLabel("—")

        information_layout.addWidget(QLabel("File"), 0, 0)
        information_layout.addWidget(self.info_file, 0, 1)

        information_layout.addWidget(QLabel("Vertices"), 1, 0)
        information_layout.addWidget(self.info_vertices, 1, 1)

        information_layout.addWidget(QLabel("Faces"), 2, 0)
        information_layout.addWidget(self.info_faces, 2, 1)

        information_layout.addWidget(QLabel("Format"), 3, 0)
        information_layout.addWidget(self.info_format, 3, 1)

        layout.addWidget(information_group)

        # Scan report
        report_group = QGroupBox("MESH ANALYSIS REPORT")
        report_layout = QVBoxLayout(report_group)

        self.report = QTextEdit()
        self.report.setReadOnly(True)
        self.report.setPlaceholderText(
            "Run SCAN MESH to inspect topology, geometry, "
            "normals, UVs and connected components."
        )
        self.report.setMinimumHeight(130)

        report_layout.addWidget(self.report)

        layout.addWidget(report_group, 2)

        return panel

    # -----------------------------------------------------------------
    # Appearance
    # -----------------------------------------------------------------

    def apply_style(self):
        apply_bone_white_theme(self)

    # -----------------------------------------------------------------
    # Image selection
    # -----------------------------------------------------------------

    def open_text_to_image(self):
        if (
            not hasattr(self, "text_to_image_window")
            or self.text_to_image_window is None
        ):
            self.text_to_image_window = TextToImageWindow(self)
            self.text_to_image_window.send_to_3d.connect(
                self.use_generated_image
            )

        self.text_to_image_window.show()
        self.text_to_image_window.raise_()
        self.text_to_image_window.activateWindow()

    def use_generated_image(self, filename: str):
        path = Path(filename)

        if not path.is_file():
            QMessageBox.warning(
                self,
                "Generated image unavailable",
                "The generated image file could not be found.",
            )
            return

        pixmap = QPixmap(str(path))

        if pixmap.isNull():
            QMessageBox.warning(
                self,
                "Invalid generated image",
                "The generated image could not be opened.",
            )
            return

        self.image_path = str(path)

        self.image_preview.setPixmap(
            pixmap.scaled(
                self.image_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        self.progress_label.setText(
            f"Generated source image: {path.name}"
        )

        self.statusBar().showMessage(
            "Generated image loaded. Ready for 3D generation."
        )

    def choose_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose source image",
            str(ROOT),
            IMAGE_FILTER,
        )

        if not filename:
            return

        self.image_path = filename

        pixmap = QPixmap(filename)

        if pixmap.isNull():
            QMessageBox.warning(
                self,
                "Invalid image",
                "The selected image could not be opened.",
            )
            self.image_path = None
            return

        self.image_preview.setPixmap(
            pixmap.scaled(
                self.image_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        self.progress_label.setText(
            f"Source image: {Path(filename).name}"
        )

        self.statusBar().showMessage(
            "Image loaded. Ready for 3D generation."
        )

    def clear_image(self):
        self.image_path = None
        self.image_preview.setPixmap(QPixmap())
        self.image_preview.setText("NO SOURCE IMAGE SELECTED")
        self.progress_label.setText("Waiting for source image.")

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.image_path:
            pixmap = QPixmap(self.image_path)

            if not pixmap.isNull():
                self.image_preview.setPixmap(
                    pixmap.scaled(
                        self.image_preview.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )

    # -----------------------------------------------------------------
    # Generation
    # -----------------------------------------------------------------

    def generate_model(self):
        if not self.image_path:
            QMessageBox.information(
                self,
                "Source image required",
                "Choose an image before generating a 3D model.",
            )
            return

        resolution = int(self.resolution_combo.currentData())

        output = unique_output_path(
            OUT / f"{Path(self.image_path).stem}_generated.glb"
        )

        self.start_worker(
            "generate",
            image_path=self.image_path,
            output_path=str(output),
            resolution=resolution,
        )

    # -----------------------------------------------------------------
    # Existing model loading
    # -----------------------------------------------------------------

    def open_large_scale_print(self):
        if self.print_window is None:
            self.print_window = LargeScalePrintWindow(
                model_path=self.model_path,
                parent=self,
            )
        else:
            self.print_window.model_path = self.model_path
            self.print_window.update_source_label()

        self.print_window.show()
        self.print_window.raise_()
        self.print_window.activateWindow()

    def open_existing_model(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open existing 3D model",
            str(OUT),
            MODEL_FILTER,
        )

        if not filename:
            return

        self.set_current_model(filename)

    def set_current_model(self, filename: str):
        path = Path(filename)

        if not path.is_file():
            QMessageBox.warning(
                self,
                "Model not found",
                f"The model file does not exist:\n{filename}",
            )
            return

        if path.suffix.lower() not in SUPPORTED_FORMATS:
            QMessageBox.warning(
                self,
                "Unsupported format",
                f"Unsupported model format: {path.suffix}",
            )
            return

        try:
            vertices, faces = inspect_model(str(path))

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Model import error",
                f"Could not inspect this model:\n\n{exc}",
            )
            return

        self.model_path = str(path.resolve())
        self.quad_model_path = None

        self.model_label.setText(path.name)

        self.info_file.setText(path.name)
        self.info_vertices.setText(f"{vertices:,}")
        self.info_faces.setText(f"{faces:,}")
        self.info_format.setText(path.suffix.upper().replace(".", ""))

        self.blender_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.quad_btn.setEnabled(True)
        self.tri_btn.setEnabled(True)

        self.viewer_message.setText(
            f"MODEL READY\n\n"
            f"{path.name}\n\n"
            f"{vertices:,} vertices\n"
            f"{faces:,} faces\n\n"
            "Select OPEN MODEL IN BLENDER to view the original model "
            "with Blender's native importer and viewport."
        )

        self.blender_status.setText("MODEL LOADED")

        self.statusBar().showMessage(
            f"Loaded model: {path.name}"
        )

    # -----------------------------------------------------------------
    # Blender launch
    # -----------------------------------------------------------------

    def open_in_maya(self):
        if not self.model_path:
            QMessageBox.information(
                self,
                "No model loaded",
                "Generate or open a model first.",
            )
            return

        model_file = Path(self.model_path).resolve()

        if not model_file.is_file():
            QMessageBox.warning(
                self,
                "Model not found",
                "The current model file no longer exists.",
            )
            return

        maya_exe = Path(
            r"C:\Program Files\Autodesk\Maya2027\bin\maya.exe"
        )

        if not maya_exe.is_file():
            QMessageBox.critical(
                self,
                "Maya not found",
                f"Expected location:\\n{maya_exe}",
            )
            return

        try:
            # Forward slashes avoid Windows path escaping in Maya's MEL command.
            model_path = str(model_file).replace("\\\\", "/")

            python_command = (
                "import maya.cmds as cmds; "
                f"cmds.file({model_path!r}, "
                "i=True, ignoreVersion=True, "
                "mergeNamespacesOnClash=False, "
                "namespace='Picture3D')"
            )

            mel_command = (
                'python("' +
                python_command.replace("\\", "\\\\").replace('"', '\\"') +
                '")'
            )

            subprocess.Popen(
                [str(maya_exe), "-command", mel_command],
                cwd=str(maya_exe.parent),
                shell=False,
            )

            self.statusBar().showMessage(
                "Launching Maya 2027 and importing the current model..."
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Maya launch failed",
                str(exc),
            )

    def open_in_blender(self):
        if not self.model_path:
            QMessageBox.information(
                self,
                "No model loaded",
                "Generate or open a model first.",
            )
            return

        if not Path(self.model_path).is_file():
            QMessageBox.warning(
                self,
                "Model not found",
                "The current model file no longer exists.",
            )
            return

        blender_exe = Path(
            os.environ.get("BLENDER_EXE", str(BLENDER_EXE))
        )

        if not blender_exe.is_file():
            QMessageBox.critical(
                self,
                "Blender not found",
                "Blender executable was not found.\n\n"
                f"Expected location:\n{blender_exe}\n\n"
                "Install Blender or set the BLENDER_EXE environment variable.",
            )
            return

        script_path = None

        try:
            # Keep the temporary script in output so Blender can read it.
            script_dir = OUT / ".blender_scripts"
            script_dir.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                prefix="open_model_",
                dir=script_dir,
                encoding="utf-8",
                delete=False,
            ) as script_file:
                script_file.write(BLENDER_VIEW_SCRIPT)
                script_path = Path(script_file.name)

            command = [
                str(blender_exe),
                "--python",
                str(script_path),
                "--",
                str(Path(self.model_path).resolve()),
            ]

            subprocess.Popen(
                command,
                cwd=str(blender_exe.parent),
                shell=False,
            )

            self.blender_status.setText("BLENDER LAUNCHING")
            self.statusBar().showMessage(
                "Launching Blender and importing the original model..."
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Blender launch failed",
                str(exc),
            )

            if script_path and script_path.exists():
                try:
                    script_path.unlink()
                except OSError:
                    pass

    # -----------------------------------------------------------------
    # Mesh scanning
    # -----------------------------------------------------------------

    def scan_current_model(self):
        if not self.model_path:
            QMessageBox.information(
                self,
                "No model loaded",
                "Open or generate a model before scanning.",
            )
            return

        self.start_worker(
            "scan",
            model_path=self.model_path,
        )

    # -----------------------------------------------------------------
    # Topology processing
    # -----------------------------------------------------------------

    def generate_quad_mesh(self):
        if not self.model_path:
            QMessageBox.information(
                self,
                "No model loaded",
                "Open or generate a model first.",
            )
            return

        source = Path(self.model_path)

        output = unique_output_path(
            OUT / f"{source.stem}_quad.obj"
        )

        self.start_worker(
            "topology",
            source=str(source),
            output=str(output),
            mode="QUAD",
            target_faces=self.quad_target.value(),
        )

    def generate_triangle_mesh(self):
        if not self.model_path:
            QMessageBox.information(
                self,
                "No model loaded",
                "Open or generate a model first.",
            )
            return

        # Use the quad result if one exists; otherwise use the current model.
        source = Path(
            self.quad_model_path
            if self.quad_model_path and Path(self.quad_model_path).is_file()
            else self.model_path
        )

        output = unique_output_path(
            OUT / f"{source.stem}_tri.glb"
        )

        self.start_worker(
            "topology",
            source=str(source),
            output=str(output),
            mode="TRI",
            target_faces=self.quad_target.value(),
        )

    # -----------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------

    def open_conversion_center(self):
        if not hasattr(self, "converter_window") or self.converter_window is None:
            self.converter_window = ConversionCenter(self)
        self.converter_window.show()
        self.converter_window.raise_()
        self.converter_window.activateWindow()

    def export_current_model(self):
        if not self.model_path:
            QMessageBox.information(
                self,
                "No model loaded",
                "Open or generate a model first.",
            )
            return

        source = Path(self.model_path)

        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export 3D model",
            str(OUT / f"{source.stem}_export.glb"),
            EXPORT_FILTER,
        )

        if not filename:
            return

        destination = Path(filename)

        if not destination.suffix:
            if "GLTF" in selected_filter:
                destination = destination.with_suffix(".gltf")
            elif "OBJ" in selected_filter:
                destination = destination.with_suffix(".obj")
            elif "STL" in selected_filter:
                destination = destination.with_suffix(".stl")
            elif "PLY" in selected_filter:
                destination = destination.with_suffix(".ply")
            elif "3MF" in selected_filter:
                destination = destination.with_suffix(".3mf")
            else:
                destination = destination.with_suffix(".glb")

        if destination.resolve() == source.resolve():
            QMessageBox.warning(
                self,
                "Invalid destination",
                "Choose a different destination so the original model "
                "is not overwritten.",
            )
            return

        self.start_worker(
            "export",
            source=str(source),
            destination=str(destination),
        )

    # -----------------------------------------------------------------
    # Background task management
    # -----------------------------------------------------------------

    def start_worker(self, task: str, **kwargs):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(
                self,
                "Task in progress",
                "Please wait for the current operation to finish.",
            )
            return

        self.set_busy(True)

        self.progress_bar.setVisible(True)
        self.progress_label.setText(
            "Working..."
        )

        self.worker = Worker(task, **kwargs)

        self.worker.progress.connect(
            self.on_worker_progress
        )

        self.worker.completed.connect(
            lambda result, current_task=task:
            self.on_worker_completed(current_task, result)
        )

        self.worker.failed.connect(
            self.on_worker_failed
        )

        self.worker.finished.connect(
            self.on_worker_finished
        )

        self.worker.start()

    def on_worker_progress(self, message: str):
        self.progress_label.setText(message)
        self.statusBar().showMessage(message)

    def on_worker_completed(self, task: str, result):
        self.progress_bar.setVisible(False)

        if task == "generate":
            self.set_current_model(str(result))

            self.progress_label.setText(
                "3D model generated successfully."
            )

            QMessageBox.information(
                self,
                "Generation complete",
                "Stable Fast 3D successfully generated your model.\n\n"
                f"{result}\n\n"
                "Use OPEN MODEL IN BLENDER to inspect the original "
                "generated geometry and textures.",
            )

        elif task == "scan":
            self.report.setPlainText(str(result))
            self.progress_label.setText("Mesh scan complete.")

        elif task == "topology":
            output = str(result)

            self.progress_label.setText(
                f"Topology processing complete: {Path(output).name}"
            )

            self.set_current_model(output)

            if Path(output).suffix.lower() == ".obj":
                self.quad_model_path = output

            QMessageBox.information(
                self,
                "Topology processing complete",
                f"Blender successfully exported:\n\n{output}",
            )

        elif task == "export":
            self.progress_label.setText(
                f"Export complete: {Path(str(result)).name}"
            )

            QMessageBox.information(
                self,
                "Export complete",
                f"Model exported successfully:\n\n{result}",
            )

    def on_worker_failed(self, message: str):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Operation failed.")

        self.statusBar().showMessage(
            "Operation failed."
        )

        QMessageBox.critical(
            self,
            "Operation failed",
            message,
        )

    def on_worker_finished(self):
        self.set_busy(False)
        self.progress_bar.setVisible(False)

        self.worker = None

    def set_busy(self, busy: bool):
        self.choose_image_btn.setEnabled(not busy)
        self.clear_image_btn.setEnabled(not busy)
        self.generate_btn.setEnabled(not busy)
        self.open_model_btn.setEnabled(not busy)
        self.print_studio_btn.setEnabled(not busy)

        self.scan_btn.setEnabled(
            not busy and self.model_path is not None
        )

        self.quad_btn.setEnabled(
            not busy and self.model_path is not None
        )

        self.tri_btn.setEnabled(
            not busy and self.model_path is not None
        )

        self.blender_btn.setEnabled(
            not busy and self.model_path is not None
        )

        self.export_btn.setEnabled(
            not busy and self.model_path is not None
        )

        self.resolution_combo.setEnabled(not busy)
        self.quad_target.setEnabled(not busy)


# ---------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Picture-to-3D Model Studio")

    window = Studio()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
