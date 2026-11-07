from pathlib import Path
import shutil
from datetime import datetime

path = Path("app/main.py")
source = path.read_text(encoding="utf-8")
original = source

import_anchor = "from app.blender_mesh import BLENDER_EXE, run_topology, scan_mesh"

if "from app.converter import ConversionCenter" not in source:
    if import_anchor not in source:
        raise SystemExit("ERROR: Could not locate blender_mesh import.")
    source = source.replace(
        import_anchor,
        import_anchor + "\nfrom app.converter import ConversionCenter",
        1
    )
    print("Added ConversionCenter import.")
else:
    print("ConversionCenter import already exists.")

if "def open_conversion_center(self):" not in source:
    method_anchor = "    def export_current_model(self):"

    if method_anchor not in source:
        raise SystemExit("ERROR: Could not locate export_current_model method.")

    method = (
        "    def open_conversion_center(self):\n"
        "        if not hasattr(self, 'converter_window') or self.converter_window is None:\n"
        "            self.converter_window = ConversionCenter(self)\n"
        "        self.converter_window.show()\n"
        "        self.converter_window.raise_()\n"
        "        self.converter_window.activateWindow()\n"
        "\n"
    )

    source = source.replace(method_anchor, method + method_anchor, 1)
    print("Added open_conversion_center method.")
else:
    print("open_conversion_center method already exists.")

if 'self.convert_btn.clicked.connect(self.open_conversion_center)' not in source:
    raise SystemExit("ERROR: Existing Conversion Center button is not connected.")

print("Existing Conversion Center button connection verified.")

if source != original:
    backup = path.with_name(
        path.name + ".backup_before_maya_format_patch_" +
        datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    shutil.copy2(path, backup)
    path.write_text(source, encoding="utf-8")
    print("Backup:", backup)
else:
    print("No main.py changes were necessary.")

print("MAIN PATCH: VERIFIED")
