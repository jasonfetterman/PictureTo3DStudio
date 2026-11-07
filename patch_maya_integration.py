from pathlib import Path
import py_compile
import sys

main_file = Path(r"C:\PictureTo3DStudio_MVP\PictureTo3DStudio\app\main.py")
source = main_file.read_text(encoding="utf-8")

# 1. Add a full-width Maya button immediately above the viewer button row.
layout_marker = """        viewer_layout.addStretch()

        viewer_buttons = QHBoxLayout()
"""

layout_replacement = """        viewer_layout.addStretch()

        self.maya_btn = QPushButton("OPEN MODEL IN MAYA")
        self.maya_btn.setObjectName("primaryButton")
        self.maya_btn.clicked.connect(self.open_in_maya)
        self.maya_btn.setEnabled(False)
        viewer_layout.addWidget(self.maya_btn)

        viewer_buttons = QHBoxLayout()
"""

if source.count(layout_marker) != 1:
    raise RuntimeError("Could not uniquely identify the viewer button layout.")

source = source.replace(layout_marker, layout_replacement, 1)

# 2. Keep Maya enabled/disabled in sync with Blender.
state_marker = "self.blender_btn.setEnabled("
state_count = source.count(state_marker)

if state_count < 1:
    raise RuntimeError("Could not find Blender button enabled-state controls.")

source = source.replace(
    state_marker,
    "self.maya_btn.setEnabled(",
)

# Restore the original Blender state calls alongside the new Maya calls.
# The original calls are reconstructed by pairing each Maya call with Blender.
lines = source.splitlines()
result = []

for line in lines:
    if "self.maya_btn.setEnabled(" in line:
        indent = line[:len(line) - len(line.lstrip())]
        result.append(line.replace("self.maya_btn.", "self.blender_btn.", 1))
        result.append(line)
    else:
        result.append(line)

source = "\n".join(result) + "\n"

# 3. Add Maya launch/import method immediately before Blender method.
method_marker = "    def open_in_blender(self):"

maya_method = '''    def open_in_maya(self):
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
            r"C:\\Program Files\\Autodesk\\Maya2027\\bin\\maya.exe"
        )

        if not maya_exe.is_file():
            QMessageBox.critical(
                self,
                "Maya not found",
                f"Maya executable was not found at:\\\\n{maya_exe}",
            )
            return

        try:
            # Maya's Python command imports the currently loaded model.
            model_path_for_maya = str(model_file).replace("\\\\\\\\", "/")
            model_literal = repr(model_path_for_maya)

            python_command = (
                "import maya.cmds as cmds; "
                f"cmds.file({model_literal}, "
                "i=True, ignoreVersion=True, "
                "mergeNamespacesOnClash=False, "
                "namespace='Picture3D')"
            )

            # Escape the Python command for Maya's MEL python() command.
            mel_command = (
                'python("'
                + python_command.replace("\\\\\\\\", "\\\\\\\\\\\\\\\\")
                                .replace('"', '\\\\\\"')
                + '")'
            )

            subprocess.Popen(
                [
                    str(maya_exe),
                    "-command",
                    mel_command,
                ],
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

'''

if source.count(method_marker) != 1:
    raise RuntimeError("Could not uniquely locate open_in_blender().")

source = source.replace(method_marker, maya_method + method_marker, 1)

# 4. Validate candidate syntax before replacing the application.
candidate = main_file.with_name("main.py.maya_candidate")
candidate.write_text(source, encoding="utf-8")

try:
    py_compile.compile(str(candidate), doraise=True)
    candidate.replace(main_file)
except Exception:
    candidate.unlink(missing_ok=True)
    raise

# 5. Verify final file and integration markers.
final_source = main_file.read_text(encoding="utf-8")
py_compile.compile(str(main_file), doraise=True)

checks = {
    "Maya button": 'QPushButton("OPEN MODEL IN MAYA")' in final_source,
    "Maya launch method": "def open_in_maya(self):" in final_source,
    "Maya executable": r"Maya2027\\bin\\maya.exe" in final_source,
    "Blender method preserved": "def open_in_blender(self):" in final_source,
    "Blender button preserved": 'QPushButton("OPEN MODEL IN BLENDER")' in final_source,
}

print("\n========== MAYA INTEGRATION VALIDATION ==========")
for label, passed in checks.items():
    print(f"{label}: {'PASS' if passed else 'FAIL'}")

if not all(checks.values()):
    raise RuntimeError("One or more integration checks failed.")

print("\nPython syntax: VALID")
print("Maya button and launcher installed.")
