# Dockerfile for running the Fragment project with OpenGL support
#
# Uses NVIDIA's OpenGL runtime base image. For machines without NVIDIA GPUs
# or the NVIDIA container runtime, replace the FROM line with an Ubuntu base
# image and install Mesa drivers for software rendering.
FROM nvidia/opengl:1.2-glvnd-runtime-ubuntu22.04

# Prevent interactive prompts from the package manager
ENV DEBIAN_FRONTEND=noninteractive

# Install required system packages
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    python3 \
    python3-pip \
    mesa-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies first to leverage Docker layer caching
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Expose VNC and noVNC ports
EXPOSE 5900 6080

# Make startup script executable and set as default command
RUN chmod +x start.sh
CMD ["./start.sh"]
