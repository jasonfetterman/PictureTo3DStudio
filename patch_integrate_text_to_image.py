from pathlib import Path

target = Path("app/main.py")
source = target.read_text(encoding="utf-8-sig")

changes = [
    (
        "from app.converter import ConversionCenter",
        "from app.converter import ConversionCenter\nfrom app.text_to_image import TextToImageWindow",
        "Text-to-Image import"
    ),
    (
        "        image_layout.addWidget(self.image_preview)\n\n        image_buttons = QHBoxLayout()",
        """        image_layout.addWidget(self.image_preview)

        self.text_to_image_btn = QPushButton("CREATE IMAGE FROM TEXT")
        self.text_to_image_btn.setObjectName("primaryButton")
        self.text_to_image_btn.setMinimumHeight(40)
        self.text_to_image_btn.clicked.connect(self.open_text_to_image)
        image_layout.addWidget(self.text_to_image_btn)

        image_buttons = QHBoxLayout()""",
        "Text-to-Image button"
    ),
    (
        "    def choose_image(self):",
        '''    def open_text_to_image(self):
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

    def choose_image(self):''',
        "Image handoff methods"
    ),
]

for old, new, label in changes:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one anchor, found {count}. "
            "No changes were written."
        )
    source = source.replace(old, new, 1)
    print("PATCHED:", label)

target.write_text(source, encoding="utf-8")
print("Updated:", target)
