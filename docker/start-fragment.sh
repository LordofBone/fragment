#!/usr/bin/env bash
set -euo pipefail

LOG_DIR=${FRAGMENT_LOG_DIR:-/var/log/fragment}
DISPLAY_NUMBER=${DISPLAY_NUMBER:-1}
DISPLAY=":${DISPLAY_NUMBER}"
export DISPLAY
export PYOPENGL_PLATFORM=${PYOPENGL_PLATFORM:-egl}
export VGL_DISPLAY=${VGL_DISPLAY:-$DISPLAY}

mkdir -p "$LOG_DIR"

start_pulseaudio() {
  if [[ "${ENABLE_PULSEAUDIO:-1}" == "0" ]]; then
    echo "PulseAudio startup disabled via ENABLE_PULSEAUDIO=0" | tee -a "$LOG_DIR/startup.log"
    return 0
  fi

  if ! command -v pulseaudio >/dev/null 2>&1; then
    echo "pulseaudio is not available on PATH" | tee -a "$LOG_DIR/startup.log"
    return 0
  fi

  pulseaudio --start \
    --log-target=file:"$LOG_DIR/pulseaudio.log" \
    --exit-idle-time=-1 \
    --disallow-exit || true
}

start_x_server() {
  if command -v Xorg >/dev/null 2>&1; then
    exec Xorg "$DISPLAY" -noreset -nolisten tcp -logfile "$LOG_DIR/Xorg.log"
  fi

  if ! command -v Xvfb >/dev/null 2>&1; then
    echo "Neither Xorg nor Xvfb is installed." >&2
    return 1
  fi

  echo "Falling back to Xvfb for display $DISPLAY" | tee -a "$LOG_DIR/startup.log"
  exec Xvfb "$DISPLAY" -screen 0 1920x1080x24 -nolisten tcp >> "$LOG_DIR/Xvfb.log" 2>&1
}

start_window_manager() {
  if command -v openbox >/dev/null 2>&1; then
    exec openbox-session >> "$LOG_DIR/openbox.log" 2>&1
  fi

  if command -v fluxbox >/dev/null 2>&1; then
    exec fluxbox >> "$LOG_DIR/fluxbox.log" 2>&1
  fi

  echo "No supported window manager found." >&2
  return 1
}

start_vnc_stack() {
  local vnc_port=${VNC_PORT:-5901}
  local web_port=${NOVNC_PORT:-8080}
  local vnc_password_flag=("-nopw")

  if [[ -n "${X11VNC_PASSWORD:-}" ]]; then
    vnc_password_flag=("-passwd" "${X11VNC_PASSWORD}")
  fi

  if ! command -v x11vnc >/dev/null 2>&1; then
    echo "x11vnc is not available." >&2
    return 1
  fi

  x11vnc -display "$DISPLAY" -forever -shared -rfbport "$vnc_port" \
    "${vnc_password_flag[@]}" -o "$LOG_DIR/x11vnc.log" &
  local vnc_pid=$!

  cleanup() {
    if kill -0 "$vnc_pid" >/dev/null 2>&1; then
      kill "$vnc_pid"
      wait "$vnc_pid" || true
    fi
  }
  trap cleanup EXIT

  if command -v websockify >/dev/null 2>&1; then
    exec websockify --web "${NOVNC_WEB_DIR:-/usr/share/novnc}" --log-file "$LOG_DIR/websockify.log" \
      "$web_port" "localhost:${vnc_port}"
  fi

  if command -v novnc_server >/dev/null 2>&1; then
    exec novnc_server --vnc "localhost:${vnc_port}" --listen "$web_port" \
      --log "$LOG_DIR/novnc.log"
  fi

  echo "No websockify/noVNC server available." >&2
  return 1
}

start_fragment() {
  cd "${FRAGMENT_APP_DIR:-/workspace/fragment}" 2>/dev/null || cd "$(dirname "$0")/.."

  if command -v vglrun >/dev/null 2>&1; then
    exec vglrun -d "$DISPLAY" python3 -u main.py >> "$LOG_DIR/fragment.log" 2>&1
  fi

  echo "vglrun not found; running without VirtualGL" | tee -a "$LOG_DIR/startup.log"
  exec python3 -u main.py >> "$LOG_DIR/fragment.log" 2>&1
}

case "${1:-}" in
  pulseaudio)
    start_pulseaudio
    ;;
  xorg)
    start_x_server
    ;;
  wm)
    start_window_manager
    ;;
  vnc)
    start_vnc_stack
    ;;
  fragment)
    start_fragment
    ;;
  start|all|"")
    start_pulseaudio
    start_x_server &
    x_pid=$!
    sleep 2
    start_window_manager &
    wm_pid=$!
    sleep 1
    start_vnc_stack &
    vnc_pid=$!
    start_fragment &
    fragment_pid=$!

    wait "$x_pid"
    wait "$wm_pid"
    wait "$vnc_pid"
    wait "$fragment_pid"
    ;;
  *)
    echo "Usage: $0 [pulseaudio|xorg|wm|vnc|fragment|start]" >&2
    exit 1
    ;;
esac
