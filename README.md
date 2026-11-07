# PictureTo3DStudio

### From a single picture to a 3D model. From an idea to a printable creation.

**Powered by Stability AI** — Image-to-3D reconstruction uses Stable Fast 3D.

**PictureTo3DStudio** is an AI-powered 3D creation studio built to bring image generation, 3D reconstruction, mesh editing, format conversion, and 3D printing preparation into one Windows desktop application.

The mission is to build a powerful, locally operated alternative to subscription-based online 3D generation services.

No mandatory cloud generation subscriptions. No per-generation fees. Your hardware, your models, your workflow.

---

## 🚀 What Is PictureTo3DStudio?

PictureTo3DStudio combines AI-powered asset creation with professional 3D workflows.

Instead of jumping between multiple applications and online services, the goal is to provide one workspace where users can:

- Generate images from text prompts.
- Turn pictures into 3D models.
- Inspect and process 3D geometry.
- Convert models between supported formats.
- Open models in Blender and Autodesk Maya.
- Scale models to virtually any desired physical size.
- Automatically divide oversized models into printable sections.
- Reassemble printed sections into complete objects.

Everything is being developed around local processing and user control.

---

## ✨ Core Features

### 🖼️ 1. Image-to-3D Generation

<escape> </escape>Turn a reference image into a textured 3D model using locally running AI.

- Load PNG, JPG, JPEG, and WEBP images.
- Remove image backgrounds before reconstruction.
- Generate 3D geometry from images.
- Generate textured 3D assets.
- Export generated models as GLB.
- Use NVIDIA CUDA acceleration.

**AI Engine:** [Stable Fast 3D](https://github.com/Stability-AI/stable-fast-3d)

### 🎨 2. Text-to-Image Generation

Create reference images directly inside the studio.

- Enter a descriptive text prompt.
- Generate images using local AI models.
- Adjust generation settings.
- Save generated images.
- Send generated images into the image-to-3D workflow.

*Status: Experimental. Model setup and complete workflow validation are ongoing.*

### 🧊 3. 3D Model Processing

A dedicated workspace for working with generated and imported 3D assets.

- Mesh inspection.
- Geometry analysis.
- Topology checks.
- Mesh cutting and splitting.
- Watertight mesh validation.
- Format conversion.
- Export preparation.

### 🛠️ 4. Blender Integration

Connect your workflow with [Blender](https://www.blender.org/).

- Open models in Blender.
- Perform advanced mesh editing.
- Use Blender's modeling and sculpting tools.
- Prepare assets for export.
- Continue editing outside the studio.

### 🎬 5. Autodesk Maya Integration

Professional modeling workflow support through [Autodesk Maya](https://www.autodesk.com/products/maya/overview).

- Open supported models in Maya.
- Work with Maya ASCII (`.ma`) files.
- Work with Maya Binary (`.mb`) files.
- Convert supported 3D formats.
- Continue professional modeling and animation workflows.

### 🖨️ 6. Large-Scale 3D Printing

**Print models larger than your printer.**

One of the major goals of PictureTo3DStudio is to make oversized 3D printing straightforward.

Users specify the physical dimensions of the finished object and the available printer build volume.

For example:

- Desired model height: 1,000 mm
- Desired model width: 600 mm
- Desired model depth: 400 mm
- Printer build volume: 220 × 220 × 250 mm

The software calculates how to divide the model into printable sections.

**Intended workflow:**

1. Import a 3D model.
2. Enter the desired final height, width, and depth.
3. Enter your printer's maximum build dimensions.
4. Scale the model to the requested physical size.
5. Automatically calculate cutting sections.
6. Split the model into printable pieces.
7. Cap cut surfaces where supported.
8. Export individual STL files.
9. Reassemble the printed pieces into the complete model.

The objective is simple: your printer's build volume should determine how the model is divided, not how large your finished creation can be.

### 🧩 7. Multi-Piece Mesh Processing

Prepare large models for segmented printing.

- Automated mesh segmentation.
- Actual geometry cutting.
- Capped cut surfaces.
- Watertight output validation.
- Individual STL exports.
- Assembly information.

The mesh cutting system has been tested using watertight geometry and capped mesh sections.

---

## 💻 Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| Desktop interface | PySide6 |
| AI inference | PyTorch |
| GPU acceleration | NVIDIA CUDA |
| Image processing | Pillow |
| 3D reconstruction | Stable Fast 3D |
| Mesh processing | Trimesh |
| Geometry operations | Shapely |
| Triangulation | Mapbox Earcut |
| 3D modeling | Blender |
| Professional modeling | Autodesk Maya |

---

## ⚙️ Hardware Requirements

PictureTo3DStudio is designed to run AI workloads locally.

**Recommended environment**

- Windows 10 or Windows 11, 64-bit.
- NVIDIA GPU with CUDA support.
- 8 GB or more system RAM recommended.
- SSD storage.
- Recent NVIDIA graphics drivers.

**Current development hardware**

| Component | Specification |
|---|---|
| GPU | NVIDIA GeForce RTX 3050 Ti Laptop |
| Dedicated VRAM | 4 GB |
| AI Framework | PyTorch |
| CUDA | 12.8 |
| Python | 3.11 recommended |

### GPU Memory Optimization

The application must account for limited GPU memory.

Generation settings should support:

- Reduced input image resolutions.
- Memory-conscious model loading.
- Efficient inference.
- CPU offloading where supported.
- Hardware-aware generation settings.

A 4 GB GPU is the current development target, so performance and memory usage are important development priorities.

---

## 🚀 Installation

### 1. Clone the repository

```powershell
git clone https://github.com/jasonfetterman/PictureTo3DStudio.git
cd PictureTo3DStudio
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure AI dependencies

Follow the Windows installation guide:

[INSTALL_AI_WINDOWS.md](INSTALL_AI_WINDOWS.md)

This covers the AI runtime and GPU-related setup.

### 6. Launch PictureTo3DStudio

```powershell
python -m app.main
```

Alternatively, launch using:

```text
Launch_PictureTo3DStudio.bat
```

---

## 📁 Project Structure

```text
PictureTo3DStudio/
│
├── app/
│   ├── main.py
│   ├── generator.py
│   ├── converter.py
│   ├── blender_mesh.py
│   ├── large_scale_print.py
│   ├── text_to_image.py
│   └── theme.py
│
├── external/
│   └── stable-fast-3d/
│
├── output/
│
├── INSTALL_AI_WINDOWS.md
├── INSTALL_APP.bat
├── Launch_PictureTo3DStudio.bat
├── requirements.txt
├── run_studio.bat
└── README.md
```

---

## 🧪 Development Status

PictureTo3DStudio is actively being developed.

| Feature | Status |
|---|---|
| Windows desktop application | In development |
| Image-to-3D generation | Integrated |
| Stable Fast 3D | Integrated |
| CUDA configuration | Configured |
| Mesh inspection | Implemented |
| Mesh conversion | In development |
| Blender integration | Implemented |
| Maya integration | In development |
| Text-to-image | Experimental |
| Large-scale mesh cutting | Developed and tested as a module |
| Large-scale printing UI integration | Pending |
| Advanced mesh refinement | Planned |
| Multi-view reconstruction | Planned |
| Windows standalone installer | Planned |

Features and compatibility may change as development continues.

---

## 🎯 The Vision

The long-term vision is to create a complete independent 3D creation platform.

PictureTo3DStudio aims to bring together:

**AI Creation**
- Text-to-image.
- Image-to-3D.
- Advanced reconstruction.
- Texture generation.

**3D Development**
- Mesh inspection.
- Mesh repair.
- Mesh refinement.
- Format conversion.
- Blender integration.
- Maya integration.

**3D Manufacturing**
- Physical dimension control.
- Automatic model scaling.
- Printer-aware segmentation.
- Multi-piece STL export.
- Assembly preparation.

The ultimate goal is to make professional 3D creation and manufacturing tools more accessible without requiring expensive online subscriptions.

---

## 🔓 Local-First Philosophy

PictureTo3DStudio is being built around three principles:

**1. Your Hardware**

Use your own computer and supported GPU hardware to run AI workloads.

**2. Your Creations**

Keep generated assets and project files under your control.

**3. Your Freedom**

Reduce dependence on subscription-based services and per-generation pricing.

Third-party AI models and libraries remain subject to their respective licenses and distribution restrictions.

---

## 📜 Licensing

PictureTo3DStudio is an independent project.

Third-party components, libraries, and AI models may have separate licenses. Refer to their respective upstream repositories and license documents before redistribution or commercial use.

---

## 👨‍💻 Developer

**Jason Fetterman**

GitHub: [@jasonfetterman](https://github.com/jasonfetterman)

Repository: [PictureTo3DStudio](https://github.com/jasonfetterman/PictureTo3DStudio)

---

<p align="center">

**PICTURE TO 3D MODEL STUDIO**

*Imagine it. Generate it. Build it. Print it.*

</p>
