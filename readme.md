# Fragment

Fragment is an advanced 3D rendering benchmark tool (inspired by 3DMark) for PCs and Raspberry Pi. It leverages OpenGL (
via PyOpenGL and Pygame) to stress-test hardware performance, with a clean graphical interface and multiple benchmark
modes.

View the full write up on [Hackster](https://www.hackster.io/314reactor/fragment)
and [Electromaker](https://www.electromaker.io/project/view/fragment)

## Features

### Benchmark Modes

1. **Shimmer** – A demo combining multiple features, including particle effects and ambient audio.  
   ![Shimmer](docs/images/Shimmer%20-%20Demo.png)

2. **Ætherial** – EMBM shader test using a pyramid model.  
   ![Ætherial](docs/images/Ætherial%20-%20EMBM%20Test.png)

3. **Eidolon** – Transparency and planar camera via EMBM shaders on spherical models.  
   ![Eidolon](docs/images/Eidolon%20-%20Transparency%20Shader%20Test.png)

4. **Treadlock** – Parallax mapping test with a spotlight on a detailed tire model.  
   ![Treadlock](docs/images/Treadlock%20-%20Parallax%20Shader%20Test.png)

5. **Gelidus** – Reflection test using cubemap-reflective water surfaces.  
   ![Gelidus](docs/images/Gelidus%20-%20Reflection%20Test.png)

6. **Baryon** – Particle system benchmark supporting CPU, Transform Feedback, and Compute Shader modes.  
   ![Baryon](docs/images/Baryon%20-%20Particle%20System%20Test.png)

### User Interface

![Main Screen - Dark Mode](docs/images/main_screen_dark_mode.png)  
![Main Screen - Light Mode](docs/images/main_screen_light_mode.png)

- Select benchmarks, configure settings, and preview scenarios.
- Tune graphical settings, including MSAA, anisotropy, shading models, and resolution.
- View performance results with clean matplotlib charts.

![Benchmark Screen](docs/images/benchmark_screen.png)  
![Results Screen](docs/images/results_screen.png)  

- Track FPS, CPU, and GPU usage in the window title bar in real-time.

![Results Screen](docs/images/benchmark_run_realtime_stats.png)

### Rendering & Performance

- **Rendering:** Diffuse, Phong, and PBR shading; parallax and shadow mapping.
- **Performance Tracking:** Real-time FPS, CPU, and GPU usage displayed in the window title bar.
- **Graphical Settings:** Adjustable resolution, MSAA, anisotropic filtering, shading models, and shadow quality.
- **Performance Score:** Aggregated FPS-based performance rating across benchmarks.

### Architecture

- **Abstract Renderer:** Manages shaders, textures, cubemaps, camera controls, and lighting.
- **Benchmark Construction:** Easily integrate model, surface, particle, and skybox-based benchmarks.

## Installation

### Prerequisites

- Python 3.10+
- Dependencies: PyOpenGL, Pygame, Matplotlib, NumPy, Pillow, psutil, GPUtil, CustomTkinter
- **Note:** `PyOpenGL-accelerate` is excluded on ARM systems due to Raspberry Pi compatibility:
  ```sh  
  PyOpenGL-accelerate==3.1.7; "arm" not in platform_machine and "aarch" not in platform_machine  
  ```

### Setup

Clone and install dependencies:

```sh  
git clone https://github.com/LordofBone/fragment.git  
cd fragment  
pip install -r requirements.txt  
```

#### Raspberry Pi Configuration

```sh  
chmod +x setup/rpi_setup.sh && ./setup/rpi_setup.sh  
chmod +x setup/rpi_bashrc_setup.sh && ./setup/rpi_bashrc_setup.sh  
```

`rpi_setup.sh` installs libosmesa6 and configures the PYOPENGL_PLATFORM and MESA_GL_VERSION_OVERRIDE envvars for
Fragment to work on the Raspberry Pi.

`rpi_bashrc_setup.sh` adds the necessary environment variables to the `.bashrc` file for Fragment to work on the
Raspberry Pi.

Sometimes just running rpi_setup.sh is enough, but if you're having trouble, try running rpi_bashrc_setup.sh as well.

## Usage

**Caution:** Fragment can be quite heavy on systems like the Raspberry Pi and may cause excessive heat buildup,
especially on the GPU. Ensure adequate cooling is in place, and use at your own risk.

Run the benchmark tool:

```sh  
python main.py  
```

Within the GUI, you can:

- Select and configure benchmark tests.
- Adjust settings such as MSAA, anisotropy, shading models, and resolution.
- Track live performance data and view overall results in Matplotlib charts.

**Note:** The results from Fragment should not be taken as totally accurate.  
The performance score is more of a "finger in the air" number at the moment, based on:  
`performance_score = overall_avg_fps * 10`.

Overall, Fragment is still a work-in-progress (WiP), so results may vary even  
upon different runs of the same benchmarks.

## Testing

Fragment includes a headless test suite using `unittest` and `pytest` to validate core functionality, including:

- Configuration parsing and renderer operations.
- Camera interpolation and performance data collection.
- Benchmark execution, audio playback, and GUI logic.

### Running Tests

To execute the test suite and generate an HTML report under the `/report` directory, run:

```sh  
pytest --html=report/report.html  
```

Alternatively, use `unittest` (no report generated):

```sh  
python -m unittest discover -s tests  
```

The generated HTML report provides a structured overview of test results for easier debugging.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Implement changes and ensure tests pass.
4. Submit a pull request.

## License

Fragment is licensed under the GNU General Public License (GPL). See the [LICENSE](LICENSE) file for details.

## Acknowledgements

Inspired by benchmarks like 3DMark and Unigine. Built using PyOpenGL, Pygame, Matplotlib, and other open-source
libraries.