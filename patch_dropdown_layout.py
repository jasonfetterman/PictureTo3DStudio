from pathlib import Path
import shutil
from datetime import datetime

path = Path("app/converter.py")
source = path.read_text(encoding="utf-8")

start = '        layout.addWidget(QLabel("SOURCE MODELS"))'
end = '        layout.addWidget(self.format_combo)'

a = source.find(start)
b = source.find(end, a)

if a < 0 or b < 0:
    raise SystemExit("Could not locate the source list and format dropdown layout.")

b += len(end)

replacement = '''        # OUTPUT FORMAT - prominently positioned at the top
        format_label = QLabel("OUTPUT FORMAT")
        format_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #20c6d5;"
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
        layout.addWidget(self.file_list)'''

backup = path.with_name(
    path.name + ".backup_before_dropdown_layout_" +
    datetime.now().strftime("%Y%m%d_%H%M%S")
)
shutil.copy2(path, backup)

source = source[:a] + replacement + source[b:]
path.write_text(source, encoding="utf-8")

print("Backup:", backup)
print("OUTPUT FORMAT moved above source list.")
print("Maya ASCII and Maya Binary entries retained.")
