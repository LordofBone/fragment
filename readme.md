# Fragment

Fragment is an advanced 3D rendering benchmark tool (inspired by 3DMark) for PCs and Raspberry Pi (4 and above on
Bookworm working during my testing). It leverages OpenGL (
via PyOpenGL and Pygame) to stress-test hardware performance, with a clean graphical interface and multiple benchmark
modes.

View the full write-up on [Hackster](https://www.hackster.io/314reactor/fragment)
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

## Known Issues

- **Raspberry Pi Compatibility:** Fragment may not work on all Raspberry Pi models or OS versions due to OpenGL
  limitations, as mentioned it works on RPi 4 and above on Bookworm.  
  Use the provided setup scripts to ensure compatibility with Raspberry Pi (Bookworm).

- **Memory Leaks:** There may be memory leaks, particularly on Raspberry Pi.  
  Running benchmarks repeatedly (especially the demo) can cause out-of-memory issues.  
  These will be investigated and addressed over time.

- **Particle System:**
   - Particles are locked to the camera position, causing them to move with it.
   - In CPU mode, particles spawn in a different location compared to other modes.
   - Ground plane rotation for particles does not always work as expected.
   - **Raspberry Pi (Bookworm):** Particles do not render identically to the PC version and appear visually different.
   - **Raspberry Pi (Bookworm):** Only `GL_POINTS` works for particle rendering; other primitive types fail under
     `glDrawArrays`.

- **Graphics Limitations (Raspberry Pi):**
   - 8× MSAA is unsupported due to GPU limitations.
   - Compute Shader mode does not function on Raspberry Pi.

- **Tone Mapping & Gamma Correction:**  
  These functions currently do not work, resulting in a washed-out image.  
  All lighting is currently rendered in SDR.

- **Performance Score:** The calculated performance score is an approximation and may not accurately represent system
  performance.

- **GUI Behavior (Raspberry Pi - Bookworm):** After running the demo, the GUI incorrectly navigates to the results
  screen instead of returning to the current tab.

## GitHub Actions & Contribution Workflow

Fragment uses GitHub Actions to automate linting, testing, and version management. These workflows ensure code quality
and maintain a structured versioning system.

### Linting, Formatting, and Testing (`lint_and_test.yml`)

This workflow runs on **every pull request**, ensuring that contributions meet coding standards and pass all tests
before merging.

#### Steps:

1. **Checkout Repository** – Fetches the latest code.
2. **Set Up Python** – Installs Python 3.10.
3. **Install Dependencies** – Installs required development dependencies.
4. **Run Ruff Linting & Formatting** –
    - Lints the code with Ruff and auto-fixes issues.
    - Ensures formatting is correct.
5. **Auto Commit Linting Fixes** – Automatically commits any formatting fixes.
6. **Run Unit Tests** – Executes tests using `pytest` and generates an HTML report (not availabe on GH pages yet).

🔹 *Why this matters:* Contributors must follow consistent coding practices, and all pull requests are automatically
checked before merging.

---

### Automatic Versioning & Tagging (`tag_and_bump_on_merge.yml`)

When a pull request is merged into the `main` branch, this workflow:

#### Steps:

1. **Checkout Repository** – Ensures full commit history is available.
2. **Set Up Python** – Installs Python 3.10.
3. **Install bump2version** – A tool for managing semantic versioning.
4. **Determine Version Bump Level** –
    - Analyzes the number of code changes (`git diff HEAD^`).
    - Determines whether to increment the **patch**, **minor**, or **major** version:
        - **Patch:** Changes < 250 lines.
        - **Minor:** Changes between 250–2000 lines.
        - **Major:** Changes ≥ 2000 lines.
5. **Bump Version** – Updates the version in the codebase accordingly.
6. **Auto Commit Version Update** – Commits the version bump change.
7. **Create a Git Tag** – Uses the updated version number as a tag (e.g., `v1.2.3`).
8. **Push Tag to Repository** – Ensures the new version is officially recorded.

🔹 *Why this matters:*

- Maintains a structured versioning approach.
- Allows easy tracking of changes over time.
- Ensures new releases are properly tagged without manual intervention.

---

### Contribution Workflow with GitHub Actions

1. **Create a Feature Branch**
    - Make changes in a new branch based on `main`.

2. **Submit a Pull Request**
    - The **lint and test workflow** runs automatically.
    - Any necessary fixes (linting, formatting) are auto-applied and committed.

3. **Merge to Main**
    - Once approved, merging triggers the **tag and version bump workflow**.
    - The repository is updated with a new version number and Git tag.

This automation ensures that every contribution is checked, formatted, and properly versioned before deployment.

---

### Notes for Contributors

- Always pull the latest changes from `main` before starting a new feature.
- If your pull request fails due to linting or formatting, let the workflow auto-correct it and push the changes.
- The versioning system is automated—there’s no need to manually update version numbers.

By following this workflow, contributions remain clean, consistent, and efficiently versioned. 🚀

## License

Fragment is licensed under the GNU General Public License (GPL). See the [LICENSE](LICENSE) file for details.

## Acknowledgements

Fragment is inspired by benchmarks like 3DMark and Unigine and is built using PyOpenGL, Pygame, Matplotlib, and other
open-source libraries.

Additional useful tools and resources utilised during development include:

- **ChatGPT** – For assisting with the Python/GLSL codebase and generating textures.
- **[Material-Map-Generator](https://github.com/joeyballentine/Material-Map-Generator)** – For generating normal,
  roughness, and height maps for textures.
- **[AudioLDM2](https://github.com/haoheliu/AudioLDM2)** – For generating the ambient music used in demo mode.
- **[sphere2cube](https://pypi.org/project/sphere2cube/)** – For converting ChatGPT-generated images into cubemaps.
- **[Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)** – For upscaling images to higher quality.