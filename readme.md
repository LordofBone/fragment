# Fragment

Fragment is an advanced 3D rendering benchmark tool (inspired by 3DMark) designed for both PCs and Raspberry Pi. It
leverages OpenGL (via PyOpenGL and Pygame) to stress-test and measure your hardware’s graphical performance. Its clean
graphical interface
and multiple benchmark modes make it particularly easy to run quick tests—especially on Raspberry Pi.

## Overview

- **Python + OpenGL:** Written in Python, using PyOpenGL and Pygame to orchestrate benchmark scenarios.
- **Multiple Benchmarks:** Includes various tests to explore performance in areas like particle systems, transparency
  effects, parallax mapping, and reflections.
- **Performance Tracking:** Real-time collection of FPS, CPU usage, and GPU usage (via psutil & GPUtil). An overall
  performance score is computed for each benchmark run.
- **Customization & GUI:** A CustomTkinter-based interface lets you select benchmarks, configure graphics parameters,
  and view results with Matplotlib-generated charts.
- **Cross-Platform:** Special setup scripts ensure that OpenGL (OSMesa) is correctly configured on Raspberry Pi.
- **Automated Testing:** A headless test suite validates configuration logic, camera interpolation, benchmark
  management, audio playback, and basic GUI functionality.

## Features

### Benchmark Modes

1. **Ætherial:**  
   ![Ætherial - EMBM Test](docs/images/Ætherial%20-%20EMBM%20Test.png)  
   EMBM shader test using a pyramid model.

2. **Eidolon:**  
   ![Eidolon - Transparency Shader Test](docs/images/Eidolon%20-%20Transparency%20Shader%20Test.png)  
   Transparency and environmental mapping (via EMBM shaders) on spherical models.

3. **Treadlock:**  
   ![Treadlock - Parallax Shader Test](docs/images/Treadlock%20-%20Parallax%20Shader%20Test.png)  
   Parallax mapping spotlight on a detailed tire model.

4. **Gelidus:**  
   ![Gelidus - Reflection Test](docs/images/Gelidus%20-%20Reflection%20Test.png)  
   Reflection test with cubemap-reflective water surfaces.

5. **Baryon:**  
   ![Baryon - Particle System Test](docs/images/Baryon%20-%20Particle%20System%20Test.png)  
   Particle system benchmark that can work in CPU, Transform Feedback, or Compute Shader mode.

6. **Shimmer:**  
   ![Shimmer - Demo](docs/images/Shimmer%20-%20Demo.png)  
   Demonstration combining most features, including particle effects and ambient audio.

### User Interface

![Main Screen](docs/images/main_screen_dark_mode.png)  
Tune graphical settings for benchmarks.

![Main Screen_Light](docs/images/main_screen_light_mode.png)  
Light mode.

![Benchmark Screen](docs/images/benchmark_screen.png)  
Select benchmarks and run tests.

![Results Screen](docs/images/results_screen.png)  
View performance charts of FPS, GPU, and CPU usage.

### Rendering Highlights

- Multiple shading model options: Diffuse, Phong, and PBR.
- Effects: parallax mapping, shadow mapping, tone mapping, gamma correction.
- Configurable MSAA and anisotropic filtering.

### Performance Metrics

- Real-time FPS, CPU usage, GPU usage; displayed in the window title bar during benchmarks.
- An aggregated performance score from average FPS across benchmarks (an indicative measure rather than a universal
  comparison).

### Graphical User Interface

- Select benchmarks, resolutions, MSAA and anisotropy levels, shading models, and other parameters.
- Preview images, interactive graphs, and a demo mode with synchronized background audio.

### Architecture

- **Abstract Renderer:** Manages shaders, textures, cubemaps, camera controls, and lighting.
- **Benchmark Construction:** Easily integrate model, surface, particle, and skybox approaches for new benchmarks.

### Cross-Platform Setup

- Scripts for Raspberry Pi handle libosmesa6 installation and environment variable configuration, ensuring compatibility
  with RPi 4 (Bookworm) and above.

## Installation

1. **Prerequisites**
   - Python 3.10+
   - PyOpenGL, Pygame, Matplotlib, NumPy, Pillow, psutil, GPUtil, CustomTkinter (and tkinter)

2. **Clone and Install**
   ```sh
   git clone https://github.com/LordofBone/fragment.git
   cd fragment
   pip install -r requirements.txt
   ```

3. **Additional Raspberry Pi Configuration**
   ```sh
   chmod +x setup/rpi_setup.sh
   ./setup/rpi_setup.sh

   chmod +x setup/rpi_bashrc_setup.sh
   ./setup/rpi_bashrc_setup.sh
   ```

## Usage

Run the main module:
```sh
python main.py
```

Within the GUI, you can:

- Select one or more benchmarks to run.
- Tune resolution, MSAA, anisotropy, shading model, shadow quality, particle render mode, and more.
- Track live performance data and view Matplotlib charts.

**Command Line Options** (optional)  
(If available, list any useful arguments or flags here.)

## Testing

A headless test suite (using unittest/pytest) validates:

- Configuration parsing and renderer functionality.
- Camera interpolation and performance data collection.
- Benchmark management and audio playback.
- GUI logic in headless mode.

Run:
```sh
pytest --html-report=./report/report.html
```

or:
```sh
python -m unittest discover -s tests
```

## Contributing

Contributions are welcome! If you have new ideas for benchmarks, optimizations, or general improvements, please:

1. Fork this repository.
2. Create a new feature branch.
3. Make changes and ensure all tests pass.
4. Submit a pull request.

## License

This project is licensed under the GNU General Public License (GPL). Refer to the LICENSE file for full details.

## Acknowledgements

Fragment draws inspiration from benchmarks provided by 3DMark, Unigine, and other industry tools. It also leverages
libraries like PyOpenGL, Pygame, and Matplotlib.