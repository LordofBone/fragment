FROM nvidia/opengl:1.2-glvnd-devel-ubuntu22.04

ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute \
    DISPLAY=:1 \
    PYOPENGL_PLATFORM=x11

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-dev \
        python3-venv \
        python3-pip \
        python3-tk \
        build-essential \
        pkg-config \
        git \
        mesa-utils \
        libglu1-mesa \
        libglu1-mesa-dev \
        libgl1-mesa-dev \
        libgles2-mesa-dev \
        libegl1 \
        libegl1-mesa \
        libegl-dev \
        libxext6 \
        libxrender1 \
        libxi6 \
        libxcursor1 \
        libxinerama1 \
        libxrandr2 \
        libxtst6 \
        libsdl2-2.0-0 \
        libsdl2-image-2.0-0 \
        libsdl2-mixer-2.0-0 \
        libsdl2-ttf-2.0-0 \
        fonts-dejavu \
        fonts-liberation \
        fonts-freefont-ttf \
        pulseaudio \
        openbox \
        supervisor \
        x11vnc \
        novnc \
        websockify \
        virtualgl \
        xvfb \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/fragment

COPY requirements.txt ./

RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python3 -m pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

COPY . /opt/fragment

COPY docker/entrypoint.sh /usr/local/bin/fragment-entrypoint.sh
COPY docker/supervisord.conf /etc/supervisor/conf.d/fragment.conf
RUN chmod +x /usr/local/bin/fragment-entrypoint.sh

EXPOSE 8080 5900

ENTRYPOINT ["/usr/local/bin/fragment-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/fragment.conf"]
