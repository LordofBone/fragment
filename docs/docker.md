# Docker / noVNC Guide

Fragment can be run inside a container that exposes a virtual desktop via noVNC. This
setup is ideal for quickly validating GPU support or hosting a self-contained
benchmark appliance without installing the Python stack directly on the host.

## Prerequisites

| Requirement | Notes |
| --- | --- |
| Docker Engine 24.0+ | Earlier releases do not include the Compose features and GPU runtime flags used below. |
| Docker Compose v2 (bundled with Docker 24+) | Required for the `docker compose` examples. |
| NVIDIA Linux driver 525+ (535+ recommended) | Must be installed natively on the host OS. Check with `nvidia-smi`. |
| NVIDIA Container Toolkit 1.14+ | Provides the `--gpus` flag and automatically injects driver libraries. |
| 64-bit host OS | Tested on Ubuntu 22.04/24.04, Debian 12, Fedora 39+, and Windows 11 via WSL2. macOS hosts are not supported because Apple GPUs do not expose the required driver stack. |

> **Tip:** After installing the NVIDIA Container Toolkit on Linux, run `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker` to enable the
> runtime hook.

## Supported host configurations

- **Native Linux (Ubuntu/Debian/Fedora/Arch):** Preferred option. Install the matching
  NVIDIA driver for your GPU and confirm `nvidia-smi` returns data before continuing.
- **Windows 11:** Use **WSL2** with GPU support (WSLg). Install the latest NVIDIA drivers
  for Windows, then install the CUDA driver inside WSL2 following NVIDIA's documentation.
  Docker Desktop must be configured to use the WSL2 engine and GPU resources must be
  shared with the selected distribution. Port forwarding from the WSL VM exposes
  `http://localhost:8080/vnc.html` to the Windows browser.
- **Linux VMs on cloud providers:** Ensure that GPU passthrough is available and that
  the VM exposes an NVIDIA GRID or equivalent device compatible with the container
  toolkit.
- **macOS:** Not supported because the container relies on NVIDIA GL libraries.

## Obtain the container image

You can **pull** a published build or **build** the image locally from the repository.

### Pull from a registry

```sh
docker pull ghcr.io/lordofbone/fragment-novnc:latest
```

Replace `latest` with a released tag if you need a specific build.

### Build locally

Clone this repository and copy the Docker assets from a release tarball before
building. The Dockerfile is not tracked in `main`, so fetch it from the
<https://github.com/LordofBone/fragment/releases> page and place the extracted
`docker/` directory alongside the repository checkout:

```sh
git clone https://github.com/LordofBone/fragment.git
cd fragment
# Download the release archive that contains docker/Dockerfile.novnc
# (replace RELEASE_TAG and ARCHIVE_NAME with the values published on the release page)
wget https://github.com/LordofBone/fragment/releases/download/RELEASE_TAG/ARCHIVE_NAME
tar -xzf ARCHIVE_NAME
cp -r path-from-archive/docker ./
docker build -t fragment-novnc -f docker/Dockerfile.novnc .
```

> Replace the placeholders with the archive name from the release you intend to use.
> If you already downloaded the tarball elsewhere, copy the `docker/` directory into
> the repository root before running `docker build`.

## Runtime configuration

### Environment toggles

The container honours the same OpenGL-related environment variables used elsewhere in
Fragment:

- `PYOPENGL_PLATFORM` – Set to `egl` (default in the image) for headless GPU rendering.
  You can switch to `osmesa` if you want to fall back to software rendering.
- `MESA_GL_VERSION_OVERRIDE` – Defaults to `3.3` to match Fragment's minimum GL
  requirement. Increase this value if you want to force a newer core profile.
- `NVIDIA_VISIBLE_DEVICES` / `NVIDIA_DRIVER_CAPABILITIES` – Automatically populated by
  Docker when you use the `--gpus` flag, but can be overridden for advanced scenarios.

Additional Fragment-specific variables can be provided as needed. For example, you can
mute all audio cues inside the container with `SDL_AUDIODRIVER=dummy`.

### Persisting benchmark output

Fragment writes CSV summaries and charts to the `report/archive/` directory inside the
repository. Mount a host directory at `/workspace/fragment/report/archive` to collect
results outside the container:

```sh
mkdir -p ./report/archive
```

## Running with Docker Compose

Create a `compose.novnc.yaml` file (you can copy the snippet below) and start the stack:

```yaml
services:
  fragment:
    image: ghcr.io/lordofbone/fragment-novnc:latest
    # Uncomment the next block if you want to build locally instead of pulling.
    # build:
    #   context: .
    #   dockerfile: docker/Dockerfile.novnc
    ports:
      - "8080:8080"  # noVNC web UI
    device_requests:
      - driver: nvidia
        count: all
        capabilities: [gpu]
    environment:
      PYOPENGL_PLATFORM: egl
      MESA_GL_VERSION_OVERRIDE: "3.3"
    volumes:
      - ./report/archive:/workspace/fragment/report/archive
```

```sh
docker compose -f compose.novnc.yaml up --pull=missing
```

The `device_requests` block mirrors `docker run --gpus all`, so the container receives
GPU access even when using the `docker compose` CLI (outside of Swarm mode).

Once the stack reports that `websockify` and `novnc` are ready, open
`http://localhost:8080/vnc.html` in a browser, click **Connect**, and you will see the
Fragment desktop session.

Stop the container with `Ctrl+C` or `docker compose down`.

## Running with `docker run`

```sh
docker run --rm \
  --gpus all \
  -p 8080:8080 \
  -e PYOPENGL_PLATFORM=egl \
  -e MESA_GL_VERSION_OVERRIDE=3.3 \
  -v $(pwd)/report/archive:/workspace/fragment/report/archive \
  ghcr.io/lordofbone/fragment-novnc:latest
```

- `--gpus all` exposes every NVIDIA GPU to the container.
- `-p 8080:8080` publishes the noVNC endpoint.
- `-v` mounts the results directory so benchmark output persists.

When the logs show the VNC server is listening, browse to
`http://localhost:8080/vnc.html` to access the GUI.

## Platform-specific caveats

- **Driver compatibility:** Ensure the NVIDIA driver on the host matches (or is newer
  than) the driver series expected by the CUDA base image used to build the container.
  Mismatched major versions (e.g., driver 510 with CUDA 12) will prevent GL contexts from
  initializing.
- **Wayland sessions on Linux:** On some distributions, Wayland sessions can interfere
  with GPU device exposure. If you encounter `EGL_BAD_ALLOC`, try logging into an X11
  session or forcing `nvidia-drm.modeset=1` in the kernel parameters.
- **Windows hybrid graphics laptops:** BIOS or vendor utilities may need to be set to
  "discrete GPU only" for WSL2 to access the NVIDIA device.
- **Headless servers:** Always verify that the GPU is accessible with `nvidia-smi` before
  launching the container. Cloud providers may require enabling persistence mode.

## Troubleshooting

- `libGL error: failed to load driver` – Confirm the NVIDIA Container Toolkit is
  installed and the `nvidia` runtime is active (`docker info | grep Runtimes`).
- Blank noVNC screen – Some browsers block mixed content. Ensure you are using HTTP or
  provide your own TLS termination in front of the container.
- Poor performance – Disable other GPU-intensive workloads on the host, and consider
  pinning the container to specific CPU cores using the `--cpuset-cpus` flag.

Once the noVNC session is open, launch the benchmark from the desktop shortcut or by
opening a terminal within the container and running `python main.py`.
