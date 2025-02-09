# Fragment

3DMark inspired OpenGL benchmark, designed for PC and Raspberry Pi 4+.

## Overview

`Fragment` is a benchmark tool inspired by 3DMark, specifically designed for PC/Raspberry Pi. It leverages OpenGL to
measure the graphical performance of your device.

## Features

- **3D Benchmarking**: Provides comprehensive benchmarking of the graphical capabilities of Raspberry Pi.
- **OpenGL**: Utilizes OpenGL and matplotlib for rendering and performance measurement.
- **Cross-Platform**: Designed to run on Raspberry PC and Pi.

## Installation

Follow these steps to set up and run the benchmark:

1. **Clone the repository**:
    ```sh
    git clone https://github.com/LordofBone/fragment.git
    cd fragment
    ```

2. **Install dependencies**:
    ```sh
    sudo apt-get update
    sudo apt-get install python3 python3-pip
    pip3 install -r requirements.txt
    ```

3. **Run the benchmark**:
    ```sh
    python3 main.py
    ```

## Benchmarks

The benchmarks included in this repository are designed to test various aspects of the graphical capabilities of a
PC/Raspberry Pi:

- **Frame Rate**: Measures the frames per second (FPS) that the device can render.
- **Performance Metrics**: Provides detailed performance metrics for analysis, such as CPU/GPU usage and displays as a
  chart.

## Graphical Capabilities

The tool leverages OpenGL to provide a graphical benchmarking experience. It includes various shaders and rendering
techniques to test the limits of your device's GPU.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements.

## License

This project is licensed under the GNU GENERAL PUBLIC License. See the [LICENSE](LICENSE) file for details.