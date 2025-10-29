FROM nvidia/opengl:1.2-glvnd-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        supervisor \
        openbox \
        x11vnc \
        novnc \
        websockify \
        pulseaudio \
        xvfb \
        virtualgl \
        xauth \
        xfonts-base \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/fragment

COPY requirements.txt ./
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker/start-fragment.sh \
    && mkdir -p /var/log/fragment

COPY docker/supervisord.conf /etc/supervisor/conf.d/fragment.conf

ENV PYOPENGL_PLATFORM=egl \
    DISPLAY=:1 \
    FRAGMENT_LOG_DIR=/var/log/fragment \
    FRAGMENT_APP_DIR=/workspace/fragment

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/fragment.conf"]
