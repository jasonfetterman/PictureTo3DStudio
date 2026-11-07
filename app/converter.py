import json
import os
import subprocess
import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QFileDialog, QComboBox, QLineEdit,
    QProgressBar, QTextEdit, QMessageBox, QCheckBox
)

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
MAYA_BIN = r"C:\Program Files\Autodesk\Maya2027\bin"
MAYAPY_EXE = os.path.join(MAYA_BIN, "mayapy.exe")

BLENDER_FORMATS = {
    "GLB (.glb)": "glb",
    "GLTF (.gltf)": "gltf",
    "FBX (.fbx)": "fbx",
    "OBJ (.obj)": "obj",
    "STL (.stl)": "stl",
    "PLY (.ply)": "ply",
}

MAYA_FORMATS = {
    "Maya ASCII (.ma)": "ma",
    "Maya Binary (.mb)": "mb",
}


def _run_process(command, log_callback):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        universal_newlines=True
    )

    for line in process.stdout:
        line = line.rstrip()
        if line:
            log_callback(line)

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(
            f"Conversion process failed with exit code {process.returncode}"
        )


def _blender_script(source, destination, output_format):
    source = str(Path(source).resolve())
    destination = str(Path(destination).resolve())

    script = r'''
import bpy
import sys
import os

args = sys.argv[sys.argv.index("--") + 1:]
source, destination, output_format = args

# Start with a clean scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

ext = os.path.splitext(source)[1].lower()

# Import source model.
if ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=source)
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=source)
elif ext == ".obj":
    bpy.ops.wm.obj_import(filepath=source)
elif ext == ".stl":
    bpy.ops.wm.stl_import(filepath=source)
elif ext == ".ply":
    bpy.ops.wm.ply_import(filepath=source)
else:
    raise RuntimeError("Unsupported Blender input format: " + ext)

# Select imported objects.
bpy.ops.object.select_all(action="SELECT")

# Export.
if output_format == "glb":
    bpy.ops.export_scene.gltf(filepath=destination, export_format="GLB")
elif output_format == "gltf":
    bpy.ops.export_scene.gltf(filepath=destination, export_format="GLTF_SEPARATE")
elif output_format == "fbx":
    bpy.ops.export_scene.fbx(filepath=destination, path_mode="COPY", embed_textures=True)
elif output_format == "obj":
    bpy.ops.wm.obj_export(filepath=destination, export_materials=True)
elif output_format == "stl":
    bpy.ops.wm.stl_export(filepath=destination)
elif output_format == "ply":
    bpy.ops.wm.ply_export(filepath=destination)
else:
    raise RuntimeError("Unsupported output format: " + output_format)

if not os.path.exists(destination):
    raise RuntimeError("Blender did not create the output file")

print("CONVERSION_OUTPUT_CREATED:", destination)
'''
    return script


def _maya_script(source, fbx_input, destination, maya_format):
    script = r'''
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds

source, fbx_input, destination, maya_format = sys.argv[1:5]

try:
    cmds.file(new=True, force=True)

    source_ext = os.path.splitext(source)[1].lower()

    if source_ext in (".ma", ".mb"):
        cmds.file(source, open=True, force=True)
    else:
        try:
            cmds.loadPlugin("fbxmaya", quiet=True)
        except Exception:
            pass

        cmds.file(fbx_input, i=True, type="FBX", ignoreVersion=True,
                  ra=True, mergeNamespacesOnClash=False,
                  namespace="ImportedModel")

    file_type = "mayaAscii" if maya_format == "ma" else "mayaBinary"

    cmds.file(rename=destination)
    cmds.file(save=True, type=file_type, force=True)

    if not os.path.exists(destination):
        raise RuntimeError("Maya did not create the output file")

    print("MAYA_OUTPUT_CREATED:", destination)

except Exception:
    traceback.print_exc()
    raise

finally:
    maya.standalone.uninitialize()
'''
    return script


def convert_one(source, output_folder, output_format, log_callback):
    source = Path(source).resolve()
    output_folder = Path(output_folder).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)

    extension = MAYA_FORMATS.get(output_format)
    if extension is None:
        extension = BLENDER_FORMATS.get(output_format)

    if extension is None:
        raise ValueError("Unsupported output format: " + output_format)

    destination = output_folder / f"{source.stem}_converted.{extension}"

    counter = 1
    while destination.exists():
        destination = output_folder / f"{source.stem}_converted_{counter}.{extension}"
        counter += 1

    if extension in BLENDER_FORMATS.values():
        script_text = _blender_script(source, destination, extension)

        with tempfile.TemporaryDirectory(prefix="picture3d_blender_") as temp:
            script_path = Path(temp) / "convert.py"
            script_path.write_text(script_text, encoding="utf-8")

            command = [
                BLENDER_EXE, "--background",
                "--python", str(script_path),
                "--", str(source), str(destination), extension
            ]

            log_callback(f"Blender conversion: {source.name}")
            _run_process(command, log_callback)

    else:
        with tempfile.TemporaryDirectory(prefix="picture3d_maya_") as temp:
            temp = Path(temp)
            maya_script = temp / "convert_to_maya.py"
            intermediate_fbx = temp / "intermediate.fbx"

            source_ext = source.suffix.lower()

            if source_ext in (".ma", ".mb"):
                fbx_for_maya = ""
            else:
                blender_script = temp / "blender_to_fbx.py"
                blender_script.write_text(
                    _blender_script(source, intermediate_fbx, "fbx"),
                    encoding="utf-8"
                )

                log_callback(f"Preparing FBX for Maya: {source.name}")

                _run_process([
                    BLENDER_EXE, "--background",
                    "--python", str(blender_script),
                    "--", str(source), str(intermediate_fbx), "fbx"
                ], log_callback)

                fbx_for_maya = str(intermediate_fbx)

            maya_script.write_text(
                _maya_script(source, fbx_for_maya, destination, extension),
                encoding="utf-8"
            )

            log_callback(f"Maya {extension.upper()} conversion: {source.name}")

            _run_process([
                MAYAPY_EXE, str(maya_script),
                str(source), fbx_for_maya, str(destination), extension
            ], log_callback)

    if not destination.exists():
        raise RuntimeError(f"Output file was not created: {destination}")

    return str(destination)


from app.theme import apply_bone_white_theme

class ConversionWorker(QThread):
    log = Signal(str)
    progress = Signal(int)
    completed = Signal(list, list)

    def __init__(self, files, output_folder, output_format):
        super().__init__()
        self.files = files
        self.output_folder = output_folder
        self.output_format = output_format

    def run(self):
        successes = []
        failures = []
        total = max(1, len(self.files))

        for index, source in enumerate(self.files):
            try:
                self.log.emit(f"\n[{index + 1}/{total}] {Path(source).name}")
                result = convert_one(
                    source,
                    self.output_folder,
                    self.output_format,
                    self.log.emit
                )
                successes.append(result)
                self.log.emit(f"SUCCESS: {result}")
            except Exception as exc:
                failures.append((source, str(exc)))
                self.log.emit(f"FAILED: {source}\n{exc}")
                self.log.emit(traceback.format_exc())

            self.progress.emit(int(((index + 1) / total) * 100))

        self.completed.emit(successes, failures)


class ConversionCenter(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Picture to 3D - Model Conversion Center")
        self.resize(760, 650)

        self.worker = None

        layout = QVBoxLayout(self)

        title = QLabel("MODEL CONVERSION CENTER")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # OUTPUT FORMAT - prominently positioned at the top
        format_label = QLabel("OUTPUT FORMAT")
        format_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #8A5A3C;"
        )
        layout.addWidget(format_label)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("outputFormatCombo")
        self.format_combo.addItems([
            "FBX (.fbx)",
            "GLB (.glb)",
            "GLTF (.gltf)",
            "OBJ (.obj)",
            "STL (.stl)",
            "PLY (.ply)",
            "Maya ASCII (.ma)",
            "Maya Binary (.mb)",
        ])
        self.format_combo.setCurrentText("FBX (.fbx)")
        self.format_combo.setMinimumHeight(42)
        layout.addWidget(self.format_combo)

        layout.addWidget(QLabel("SOURCE MODELS"))

        file_buttons = QHBoxLayout()
        self.add_button = QPushButton("ADD MODELS")
        self.remove_button = QPushButton("REMOVE SELECTED")
        self.clear_button = QPushButton("CLEAR LIST")

        file_buttons.addWidget(self.add_button)
        file_buttons.addWidget(self.remove_button)
        file_buttons.addWidget(self.clear_button)
        layout.addLayout(file_buttons)

        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(100)
        self.file_list.setSelectionMode(
            self.file_list.SelectionMode.ExtendedSelection
        )
        layout.addWidget(self.file_list)

        layout.addWidget(QLabel("OUTPUT FOLDER"))

        folder_row = QHBoxLayout()
        self.output_folder = QLineEdit(
            str(Path.home() / "Documents" / "PictureTo3D_Converted")
        )
        self.folder_button = QPushButton("BROWSE")
        folder_row.addWidget(self.output_folder)
        folder_row.addWidget(self.folder_button)
        layout.addLayout(folder_row)

        self.preserve_check = QCheckBox(
            "Preserve materials and textures where supported"
        )
        self.preserve_check.setChecked(True)
        layout.addWidget(self.preserve_check)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        layout.addWidget(QLabel("CONVERSION LOG"))

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        action_row = QHBoxLayout()
        self.convert_button = QPushButton("START CONVERSION")
        self.close_button = QPushButton("CLOSE")
        action_row.addWidget(self.convert_button)
        action_row.addWidget(self.close_button)
        layout.addLayout(action_row)

        self.add_button.clicked.connect(self.add_files)
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button.clicked.connect(self.file_list.clear)
        self.folder_button.clicked.connect(self.choose_folder)
        self.convert_button.clicked.connect(self.start_conversion)
        self.close_button.clicked.connect(self.close)

        apply_bone_white_theme(self)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Models",
            "",
            "3D Models (*.glb *.gltf *.fbx *.obj *.stl *.ply *.ma *.mb)"
        )

        existing = {
            self.file_list.item(i).text()
            for i in range(self.file_list.count())
        }

        for file in files:
            if file not in existing:
                self.file_list.addItem(file)

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Output Folder", self.output_folder.text()
        )
        if folder:
            self.output_folder.setText(folder)

    def append_log(self, message):
        self.log_view.append(message)

    def start_conversion(self):
        files = [
            self.file_list.item(i).text()
            for i in range(self.file_list.count())
        ]

        if not files:
            QMessageBox.warning(self, "No Models", "Add at least one model first.")
            return

        folder_text = self.output_folder.text().strip()
        if not folder_text:
            QMessageBox.warning(self, "No Folder", "Choose an output folder.")
            return

        folder = Path(folder_text)
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(self, "Folder Error", str(exc))
            return

        output_format = self.format_combo.currentText()

        self.progress_bar.setValue(0)
        self.log_view.clear()
        self.convert_button.setEnabled(False)
        self.add_button.setEnabled(False)

        self.worker = ConversionWorker(files, str(folder), output_format)
        self.worker.log.connect(self.append_log)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.completed.connect(self.conversion_finished)
        self.worker.start()

    def conversion_finished(self, successes, failures):
        self.convert_button.setEnabled(True)
        self.add_button.setEnabled(True)

        self.append_log("\n========== CONVERSION SUMMARY ==========")
        self.append_log(f"Successful: {len(successes)}")
        self.append_log(f"Failed: {len(failures)}")

        if failures:
            QMessageBox.warning(
                self,
                "Conversion Finished",
                f"Completed {len(successes)} conversion(s).\n"
                f"{len(failures)} conversion(s) failed.\n"
                "See the conversion log for details."
            )
        else:
            QMessageBox.information(
                self,
                "Conversion Finished",
                f"Successfully converted {len(successes)} model(s)."
            )

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Conversion Running",
                "Wait for the current conversion to finish before closing."
            )
            event.ignore()
            return
        event.accept()
