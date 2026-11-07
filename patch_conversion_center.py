from pathlib import Path

main_path = Path("app/main.py")
source = main_path.read_text(encoding="utf-8")

import_anchor = "from app.blender_mesh import BLENDER_EXE, run_topology, scan_mesh"

if "from app.converter import ConversionCenter" not in source:
    if import_anchor not in source:
        raise SystemExit("Could not find the verified blender_mesh import anchor.")
    source = source.replace(
        import_anchor,
        import_anchor + "\nfrom app.converter import ConversionCenter",
        1
    )

button_anchor = "viewer_buttons.addWidget(self.blender_btn)\nviewer_buttons.addWidget(self.export_btn)"

button_code = (
    button_anchor
    + "\n"
    + "        self.conversion_center_btn = QPushButton(\"OPEN MODEL CONVERSION CENTER\")\n"
    + "        self.conversion_center_btn.clicked.connect(self.open_conversion_center)\n"
    + "        viewer_buttons.addWidget(self.conversion_center_btn)"
)

if "self.conversion_center_btn" not in source:
    if button_anchor not in source:
        raise SystemExit("Could not find the verified viewer_buttons anchor.")
    source = source.replace(button_anchor, button_code, 1)

method_anchor = "    def export_current_model(self):"

method_code = (
    "    def open_conversion_center(self):\n"
    "        if not hasattr(self, \"converter_window\") or self.converter_window is None:\n"
    "            self.converter_window = ConversionCenter(self)\n"
    "        self.converter_window.show()\n"
    "        self.converter_window.raise_()\n"
    "        self.converter_window.activateWindow()\n"
    "\n"
    + method_anchor
)

if "def open_conversion_center(self):" not in source:
    if method_anchor not in source:
        raise SystemExit("Could not find export_current_model method anchor.")
    source = source.replace(method_anchor, method_code, 1)

main_path.write_text(source, encoding="utf-8")
print("MAIN PATCHES: 3")
