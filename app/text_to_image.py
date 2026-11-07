from __future__ import annotations

import traceback
from pathlib import Path

import torch

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QGroupBox,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "generated_images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "stabilityai/sd-turbo"


from app.theme import apply_bone_white_theme

class ImageGenerationWorker(QThread):
    progress = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, prompt: str, width: int, height: int):
        super().__init__()
        self.prompt = prompt
        self.width = width
        self.height = height

    def run(self):
        try:
            self.progress.emit("Loading SD-Turbo model...")

            from diffusers import StableDiffusionPipeline

            if not torch.cuda.is_available():
                raise RuntimeError(
                    "CUDA is unavailable. Text-to-Image requires a CUDA GPU."
                )

            pipe = StableDiffusionPipeline.from_pretrained(
                MODEL_ID,
                torch_dtype=torch.float16,
                use_safetensors=True,
            )

            self.progress.emit("Preparing low-VRAM GPU mode...")

            pipe.enable_model_cpu_offload()
            pipe.enable_attention_slicing("max")

            self.progress.emit("Generating image...")

            result = pipe(
                prompt=self.prompt,
                width=self.width,
                height=self.height,
                num_inference_steps=4,
                guidance_scale=0.0,
            )

            image = result.images[0]

            from datetime import datetime

            filename = (
                "generated_"
                + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                + ".png"
            )

            destination = OUTPUT_DIR / filename
            image.save(destination)

            del result
            del pipe
            torch.cuda.empty_cache()

            self.completed.emit(str(destination))

        except Exception:
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

            self.failed.emit(traceback.format_exc())


class TextToImageWindow(QDialog):
    send_to_3d = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Text-to-Image Studio")
        self.resize(850, 760)
        self.setMinimumSize(650, 600)

        self.generated_path: str | None = None
        self.worker: ImageGenerationWorker | None = None

        self.build_ui()
        self.apply_style()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("TEXT-TO-IMAGE STUDIO")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel(
            "LOCAL AI IMAGE GENERATION  /  SD-TURBO  /  CUDA"
        )
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        prompt_group = QGroupBox("01  /  IMAGE DESCRIPTION")
        prompt_layout = QVBoxLayout(prompt_group)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText(
            "Describe the object you want to create..."
        )
        self.prompt_input.setMinimumHeight(42)
        prompt_layout.addWidget(self.prompt_input)

        layout.addWidget(prompt_group)

        settings_row = QHBoxLayout()

        settings_row.addWidget(QLabel("IMAGE SIZE"))

        self.size_combo = QComboBox()
        self.size_combo.addItem("512 x 512", 512)
        self.size_combo.addItem("448 x 448", 448)
        self.size_combo.addItem("384 x 384", 384)
        settings_row.addWidget(self.size_combo)

        settings_row.addStretch()

        self.generate_btn = QPushButton("GENERATE IMAGE")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setMinimumHeight(42)
        self.generate_btn.clicked.connect(self.generate_image)
        settings_row.addWidget(self.generate_btn)

        layout.addLayout(settings_row)

        preview_group = QGroupBox("02  /  GENERATED IMAGE")
        preview_layout = QVBoxLayout(preview_group)

        self.preview = QLabel("YOUR GENERATED IMAGE WILL APPEAR HERE")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(340)
        self.preview.setObjectName("preview")
        self.preview.setScaledContents(False)

        preview_layout.addWidget(self.preview)
        layout.addWidget(preview_group, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.status = QLabel("Ready. Enter a description to begin.")
        self.status.setObjectName("status")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()

        self.save_btn = QPushButton("SAVE IMAGE AS...")
        self.save_btn.setObjectName("secondaryButton")
        self.save_btn.clicked.connect(self.save_image)
        self.save_btn.setEnabled(False)
        buttons.addWidget(self.save_btn)

        self.send_btn = QPushButton("SEND TO 3D")
        self.send_btn.setObjectName("primaryButton")
        self.send_btn.clicked.connect(self.send_image_to_3d)
        self.send_btn.setEnabled(False)
        buttons.addWidget(self.send_btn)

        layout.addLayout(buttons)

    def apply_style(self):
        apply_bone_white_theme(self)

    def generate_image(self):
        prompt = self.prompt_input.text().strip()

        if not prompt:
            QMessageBox.information(
                self,
                "Description required",
                "Enter a description for the image first.",
            )
            return

        if self.worker is not None and self.worker.isRunning():
            return

        size = int(self.size_combo.currentData())

        self.generate_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.progress.show()
        self.status.setText("Starting local image generation...")

        self.worker = ImageGenerationWorker(
            prompt,
            size,
            size,
        )

        self.worker.progress.connect(self.status.setText)
        self.worker.completed.connect(self.on_generation_completed)
        self.worker.failed.connect(self.on_generation_failed)
        self.worker.finished.connect(self.on_worker_finished)

        self.worker.start()

    def on_generation_completed(self, filename: str):
        self.generated_path = filename

        pixmap = QPixmap(filename)

        if pixmap.isNull():
            self.status.setText("Image saved, but preview could not be loaded.")
            return

        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        self.save_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status.setText(
            f"Image generated: {Path(filename).name}"
        )

    def on_generation_failed(self, error: str):
        self.status.setText("Image generation failed.")
        QMessageBox.critical(
            self,
            "Image Generation Error",
            error[-5000:],
        )

    def on_worker_finished(self):
        self.progress.hide()
        self.generate_btn.setEnabled(True)

    def save_image(self):
        if not self.generated_path:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save generated image",
            str(Path(self.generated_path).with_suffix(".png")),
            "PNG image (*.png)",
        )

        if not filename:
            return

        import shutil

        destination = Path(filename)

        if destination.suffix.lower() != ".png":
            destination = destination.with_suffix(".png")

        shutil.copy2(self.generated_path, destination)
        self.status.setText(f"Saved: {destination.name}")

    def send_image_to_3d(self):
        if self.generated_path and Path(self.generated_path).is_file():
            self.send_to_3d.emit(self.generated_path)
            self.status.setText("Image sent to the 3D workspace.")

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.generated_path:
            pixmap = QPixmap(self.generated_path)

            if not pixmap.isNull():
                self.preview.setPixmap(
                    pixmap.scaled(
                        self.preview.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(
                self,
                "Generation in progress",
                "Wait for image generation to finish before closing this window.",
            )
            event.ignore()
            return

        event.accept()
