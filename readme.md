# Fragment

Fragment is an advanced 3D rendering benchmark tool inspired by 3DMark. Designed to run on both PCs and Raspberry Pi
devices, it uses modern OpenGL techniques to stress-test and measure the graphical performance of your hardware. With a
modular architecture and multiple benchmark scenarios, Fragment is ideal for a fun and quick test of hardware,
especially Raspberry Pi.

## Overview

Fragment is written in Python and leverages OpenGL (via PyOpenGL and Pygame) to create a suite of benchmarks to create
rendering scenarios. It incorporates:

- **Multiple Benchmark Modes:** Each mode (Baryon, Eidolon, Gelidus, Shimmer, Treadlock, Ætherial) tests a different
  aspect of graphics performance—from particle systems and transparency effects to advanced parallax mapping and
  reflective surfaces.
- **Modular Renderer:** An abstract renderer framework that manages shader initialization, texture loading (including
  cubemaps), camera control, shadow mapping, and dynamic rendering options such as parallax mapping, tone mapping, and
  gamma correction.
- **Performance Monitoring:** Real-time collection of FPS, CPU usage (via psutil), and GPU usage (via GPUtil), all
  collated by a dedicated stats collector that computes an overall performance score.
- **Customizable GUI:** A user interface built with CustomTkinter that allows you to select benchmarks, adjust rendering
  parameters, and view results through graphs (powered by Matplotlib).
- **Cross-Platform Compatibility:** Special setup scripts for Raspberry Pi ensure that OpenGL rendering via OSMesa is
  correctly configured.
- **Automated Testing:** A headless test suite validates configuration logic, camera interpolation, benchmark
  management, audio playback, and basic GUI interactions.

## Features

- **Diverse Benchmark Tests:**
    - **Baryon:** Particle system benchmark featuring particle generation, physics and can operate via the CPU,
      Transform Feedback, or Compute Shader.
    - **Eidolon:** Tests transparency and environmental mapping using EMBM shaders and planar rendering on spherical a
      model.
    - **Gelidus:** A reflection test benchmark that renders water surfaces with cubemap reflections.
    - **Treadlock:** A parallax mapping shader test focusing on detailed tire model rendering using parallax mapping.
    - **Ætherial:** An EMBM shader benchmark using a pyramid model to test the basics of a GPU.
    - **Shimmer:** A combination demo that integrates most of the benchmark features, particle effects, and ambient
      audio.

- **High-Fidelity Rendering:**
    - Supports multiple shading models (Diffuse, Phong, PBR).
    - Effects such as parallax mapping, shadow mapping, tone mapping, and gamma correction.
    - Configurable MSAA and anisotropic filtering for improved visual quality.

- **Performance Metrics:**
    - Real-time FPS, CPU, and GPU usage tracking.
    - A performance score is calculated from the aggregated data for each benchmark run (not to be taken as a
      definitive/comparable measure of performance).

- **Graphical User Interface:**
    - CustomTkinter–based UI for selecting benchmarks and configuring parameters (resolution, MSAA, anisotropy, shading
      model, shadow quality, and particle render mode).
    - Preview images and interactive graphs display benchmark results.
    - A demo mode that integrates background audio (using the AudioPlayer class) for a more immersive demo experience.

- **Extensible Architecture:**
    - The `AbstractRenderer` module encapsulates core rendering functions including shader management, texture and
      cubemap loading, camera control, and lighting setup.
    - Additional renderers (model, surface, particle, skybox) are easily integrated via the configuration functions.

- **Cross-Platform Setup:**
    - Includes bash scripts for Raspberry Pi configuration:
        - `setup/rpi_setup.sh`: Installs the required libosmesa6 package and sets OpenGL environment variables.
        - `setup/rpi_bashrc_setup.sh`: Appends persistent exports to ensure settings are retained across sessions.

- **Unit Testing Suite:**
    - Automated tests (using unittest and pytest) cover configuration, camera interpolation, scene construction,
      benchmark management, audio playback, and GUI logic.
    - Headless tests avoid OpenGL calls so CI can run without a GPU context.

## Installation

### Prerequisites

- **Python 3.7+**
- OpenGL (via PyOpenGL)
- Pygame
- Matplotlib, NumPy, Pillow
- psutil, GPUtil
- CustomTkinter (and tkinter)

Make sure to install all dependencies as listed in the `requirements.txt` file.

### Clone and Install

Clone the repository:

```sh
git clone https://github.com/LordofBone/fragment.git
cd fragment
```

Install dependencies:

```sh
pip install -r requirements.txt
```

### Raspberry Pi Setup

If you’re running on a Raspberry Pi, execute the following scripts:

1. Install libosmesa6 and set environment variables:

   ```sh
   chmod +x setup/rpi_setup.sh
   ./setup/rpi_setup.sh
   ```

2. Persist environment variables:

   ```sh
   chmod +x setup/rpi_bashrc_setup.sh
   ./setup/rpi_bashrc_setup.sh
   ```

These scripts set variables such as `PYOPENGL_PLATFORM=osmesa` and `MESA_GL_VERSION_OVERRIDE=3.3`, ensuring OpenGL works
correctly on headless or Pi systems.

## Usage

### Running Benchmarks via Command Line

You can run Fragment by invoking the main module:

```sh
python main.py
```

Within the GUI you can:

- Select one or more benchmark tests.
- Adjust parameters such as resolution, MSAA level, anisotropy, shading model, shadow quality, and particle render mode.
- View live performance data and charts generated by Matplotlib.
- Run a demo mode that includes synchronized background audio.

### Benchmark Parameters

Configure settings such as:

- Resolution: Choose from common resolutions or Fullscreen mode.
- MSAA Level: (0, 2, 4, 8)
- Anisotropy Level: (1, 2, 4, 8, 16)
- Shading Model: Diffuse, Phong, or PBR.
- Shadow Map Resolution: (None, 1024x1024, 2048x2048, 4096x4096)
- Particle Render Mode: Options include CPU, Transform Feedback, or Compute Shader.
- V-Sync and Audio: Enable or disable for smoother performance and demo playback.

### Architecture

**Benchmark Manager**  
The `BenchmarkManager` runs selected benchmarks in separate processes and collects performance data (FPS, CPU, GPU
usage) via the `StatsCollector`. It computes an overall performance score based on average FPS across benchmarks.

## Abstract Renderer

At the heart of Fragment is the `AbstractRenderer` class which:

- Initializes and manages shader programs.
- Loads textures and cubemaps.
- Implements shadow mapping and camera control.
- Provides helper decorators for common OpenGL state setups.
- Supports advanced effects like parallax mapping and tone mapping.

### Testing

A unit test suite is provided to ensure confidence in functionality:

- **Configuration and Renderer Tests:** Verify that `RendererConfig` correctly processes model, surface, skybox, and
  particle renderer parameters.
- **Camera and Stats Tests:** Ensure that `CameraController` interpolates positions correctly and `StatsCollector`
  gathers performance data.
- **Benchmark Manager and Audio Tests:** Validate benchmark process management and audio playback without requiring
  actual hardware access.
- **GUI Tests:** Run in headless mode to simulate user interactions and verify display logic.

Run tests with:

```sh
pytest --html-report=./report/report.html
```

Or using Python’s unittest discovery:

```sh
python -m unittest discover -s tests
```

## Contributing

Contributions are very welcome! If you have ideas for new benchmarks, improvements in the rendering pipeline, or GUI
enhancements, please fork the repository, create a new branch, and submit a pull request. Ensure that your changes pass
all tests and adhere to the project’s coding guidelines.

## License

This project is licensed under the GNU General Public License (GPL). See the LICENSE file for full details.

## Acknowledgements

Fragment is developed from inspiration by the benchmarks made by 3DMark. Many thanks to the contributors and open-source
libraries that make this project possible.