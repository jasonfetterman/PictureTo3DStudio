# PictureTo3DStudio

### Turn ideas and images into 3D models. Create, edit, convert, and prepare them for printing—all in one desktop studio.

**PictureTo3DStudio** is an AI-powered 3D creation application designed to bring image generation, 3D reconstruction, mesh processing, and 3D printing preparation into one Windows desktop workspace.

Built with Python, PyTorch, CUDA, and a collection of professional 3D tools, the goal is simple: give creators the ability to build and work with 3D assets locally, without depending on expensive subscription-based generation services.

---

## ✨ Features

### 🖼️ Image-to-3D Generation
Transform an input image into a textured 3D model using locally running AI models.

- Generate 3D assets from images.
- Remove image backgrounds before reconstruction.
- Generate textured 3D geometry.
- Export generated models as GLB.
- Run inference using a compatible NVIDIA GPU.

Powered by [Stable Fast 3D](https://github.com/Stability-AI/stable-fast-3d).

### 🎨 Text-to-Image Generation
Create images from written prompts as part of the asset creation workflow.

- Enter a text prompt.
- Generate images locally using AI models.
- Use generated images as input for 3D reconstruction.

*Experimental: model setup and end-to-end generation are still being developed.*

### 🧊 3D Model Processing
Work with 3D assets inside one application.

- Inspect mesh topology.
- Analyze mesh geometry.
- Convert supported 3D formats.
- Prepare assets for other 3D applications.
- Export models for additional editing.

### 🛠️ Blender Integration
Connect your workflow with [Blender](https://www.blender.org/).

- Open models in Blender.
- Use Blender for advanced editing.
- Access Blender-based mesh processing.
- Prepare models for export and printing.

### 🎬 Autodesk Maya Integration
Connect with [Autodesk Maya](https://www.autodesk.com/products/maya/overview).

- Open supported models in Maya.
- Convert supported Maya formats.
- Continue editing assets in a professional 3D environment.

### 🖨️ Large-Scale 3D Printing
Create models larger than your printer's build volume.

The planned large-scale printing workflow allows users to:

1. Specify the desired final model dimensions: **Height × Width × Depth**.
2. Enter the available printer build volume.
3. Scale the model to the desired dimensions.
4. Automatically divide the model into printable sections.
5. Export individual pieces for printing.
6. Reassemble the sections into the complete model.

The objective is to make printing oversized objects practical with ordinary desktop 3D printers.

### 🧩 Multi-Piece Mesh Processing
Prepare large models for segmented printing.

- Split meshes into smaller sections.
- Generate capped, printable pieces.
- Preserve mesh integrity where supported.
- Export individual STL parts.
- Generate assembly information.

---

## 💻 Technology

| Component | Technology |
|---|---|
| Programming language | Python |
| Desktop interface | PySide6 |
| AI inference | PyTorch |
| GPU acceleration | NVIDIA CUDA |
| Image processing | Pillow |
| 3D mesh processing | Trimesh |
| Geometry operations | Shapely |
| Mesh triangulation | Mapbox Earcut |
| AI reconstruction | Stable Fast 3D |
| 3D editing | Blender |
| Professional modeling | Autodesk Maya |

---

## ⚙️ Hardware Requirements

PictureTo3DStudio is designed around local hardware rather than cloud-based generation services.

**Recommended hardware**
- Windows 10 or Windows 11, 64-bit
- NVIDIA GPU with CUDA support
- 8 GB or more system RAM recommended
- SSD storage
- Recent NVIDIA drivers

**Current development hardware**
- NVIDIA GeForce RTX 3050 Ti Laptop GPU
- 4 GB dedicated VRAM
- PyTorch with CUDA 12.8

GPU memory is limited, so AI generation settings must be configured carefully. Lower image resolutions and memory-conscious inference settings are important on GPUs with 4 GB VRAM.

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

For GPU-enabled AI generation, install a PyTorch build compatible with your NVIDIA driver and CUDA environment. Follow the project's Windows AI installation guide:

[INSTALL_AI_WINDOWS.md](INSTALL_AI_WINDOWS.md)

### 5. Launch the application

```powershell
python -m app.main
```

Alternatively, use:

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

## 🎯 Project Vision

The long-term goal is to develop an independent, locally operated 3D creation studio.

Rather than relying on multiple paid online services, PictureTo3DStudio aims to bring the major stages of 3D asset creation together:

- AI image generation.
- Image-to-3D reconstruction.
- Mesh refinement.
- 3D model conversion.
- Blender and Maya workflows.
- Automated mesh preparation.
- Oversized model segmentation.
- 3D printing and assembly preparation.

The focus is accessibility, local processing, creative freedom, and control over the entire workflow.

---

## 🧪 Development Status

PictureTo3DStudio is actively under development.

| Feature | Status |
|---|---|
| Desktop application | In development |
| Image-to-3D generation | Integrated |
| Stable Fast 3D | Integrated |
| CUDA support | Configured |
| Mesh inspection | Implemented |
| Mesh conversion | In development |
| Blender integration | Implemented |
| Maya integration | In development |
| Text-to-image | Experimental |
| Large-scale printing | Processing module developed; application integration pending |
| Automated mesh refinement | Planned |
| Advanced multi-view reconstruction | Planned |

Features and compatibility may change as development continues.

---

## 🔓 Local-First Development

PictureTo3DStudio is being developed with a local-first philosophy.

The objective is to:
- Reduce dependence on subscription-based AI services.
- Run supported AI workloads on the user's own hardware.
- Give users control over their generated assets.
- Keep the creation workflow in one desktop application.
- Make advanced 3D workflows more accessible.

Some AI models and third-party tools have their own licensing terms, hardware requirements, and distribution restrictions. Please review their licenses before using or redistributing them.

---

## 📜 License

The project's license and the licenses of included third-party components and AI models must be respected independently. See the relevant upstream projects for their licensing terms.

---

## 👨‍💻 Author

**Jason Fetterman**

GitHub: [@jasonfetterman](https://github.com/jasonfetterman)

Project: [PictureTo3DStudio](https://github.com/jasonfetterman/PictureTo3DStudio)

---

*From a single picture to a printable 3D creation.*
