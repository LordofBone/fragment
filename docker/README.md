# Fragment Docker Quickstart

This directory contains GPU-ready container assets for running the Fragment
benchmark suite. The configuration targets environments with NVIDIA GPUs and
bind-mounts the repository's `report/` and `screenshots/` folders so that result
artifacts persist outside the container.

## Prerequisites

1. **Docker Engine 20.10+** with Compose V2 (`docker compose`).
2. **NVIDIA GPU drivers** installed on the host.
3. **NVIDIA Container Toolkit** so CUDA workloads can reach the GPU:
   - Linux: follow the official installation guide – <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>.
   - Windows/WSL2: install the Windows driver first, then enable WSL2 integration
     and install the toolkit inside your Linux distribution using the same guide
     as above. Reboot once the toolkit is installed so `nvidia-smi` works inside WSL2.

## Port forwarding notes

Fragment exposes port **8080** inside the container (for remote desktops,
telemetry, or auxiliary services you may start). On Linux the mapping in the
Compose file (`8080:8080`) is sufficient. For Windows hosts running through
WSL2 you must forward the port to Windows if you want to access it from the
Windows side:

```powershell
# Run in an elevated PowerShell prompt
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=127.0.0.1
```

Remove the mapping with `netsh interface portproxy delete v4tov4 listenport=8080`.

## Environment variables

You can tune Fragment's behaviour via environment variables. They work with both
`docker run` and Compose (see the `environment` section in
`docker-compose.fragment.yml`).

| Variable | Description | Default |
| --- | --- | --- |
| `FRAGMENT_FULLSCREEN` | Force fullscreen rendering when set to a truthy value (`1`, `true`, `on`, etc.). | Uses the in-app selection. |
| `FRAGMENT_AUDIO_ENABLED` | Enable (`true`) or disable (`false`) background audio playback. | Enabled. |
| `FRAGMENT_DEBUG_MODE` | Emit verbose renderer diagnostics and capture additional debug assets. | Disabled. |

If an environment variable is unset the GUI's own settings remain in control.

## Example commands

### Linux

```bash
# Build and start the GPU-enabled stack
cd /path/to/fragment
FRAGMENT_FULLSCREEN=true docker compose -f docker/docker-compose.fragment.yml up --build

# Alternatively run a single container without Compose
docker build -t fragment -f docker/Dockerfile.fragment .
docker run --rm -it --gpus all \
  -e DISPLAY=$DISPLAY \
  -e FRAGMENT_AUDIO_ENABLED=false \
  -p 8080:8080 \
  -v "$PWD/report:/app/report" \
  -v "$PWD/screenshots:/app/screenshots" \
  fragment
```

### Windows / WSL2

```powershell
# From PowerShell (assumes Docker Desktop + WSL integration)
cd C:\path\to\fragment
$env:FRAGMENT_DEBUG_MODE = "true"
docker compose -f docker/docker-compose.fragment.yml up --build

# Plain docker run via PowerShell
$env:FRAGMENT_AUDIO_ENABLED = "false"
docker build -t fragment -f docker/Dockerfile.fragment .
docker run --rm -it --gpus all `
  -p 8080:8080 `
  -e FRAGMENT_FULLSCREEN=true `
  -v ${PWD}/report:/app/report `
  -v ${PWD}/screenshots:/app/screenshots `
  fragment
```

> **Tip:** When running under WSL2 with an X server (VcXsrv/X410), forward your
> `DISPLAY` and audio variables (`PULSE_SERVER`) to the container so the GUI can
> appear on Windows. Docker Desktop's "Use host networking" option for Linux
> containers simplifies this setup.

