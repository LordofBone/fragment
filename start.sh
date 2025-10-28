#!/bin/bash
# Startup script to launch virtual display, VNC, noVNC, and the Fragment app
set -e

XVFB_WHD="${XVFB_WHD:-1280x720x24}"

# Start X virtual framebuffer
Xvfb :0 -screen 0 ${XVFB_WHD} &
XVFB_PID=$!

# Start lightweight window manager
fluxbox >/var/log/fluxbox.log 2>&1 &

# Start VNC server
x11vnc -display :0 -forever -shared -rfbport 5900 >/var/log/x11vnc.log 2>&1 &

# Start websockify/noVNC
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/var/log/websockify.log 2>&1 &

# Ensure display variable is set
export DISPLAY=:0

# Launch application
python3 main.py

# Cleanup
kill $XVFB_PID
