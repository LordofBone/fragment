#!/bin/bash
#
# This script installs the required package `libosmesa6` and sets up environment variables
# for OpenGL rendering with OSMesa.
#
# Usage:
# 1. Make the script executable: chmod +x setup.sh
# 2. Run it: ./setup.sh
#
# Notes:
# - If `apt-get` fails to find `libosmesa6`, try running `sudo apt-get update` manually.
# - The environment variables (`export` commands) are set in this script, but they may
#   not persist in new terminal sessions. If they do not work as expected, try running them
#   manually or using the `persistent_exports.sh` script.
#

# Update package lists
sudo apt-get update && sudo apt-get install -y libosmesa6

# Check if libosmesa6 installed successfully
if dpkg -l | grep -q libosmesa6; then
    echo "libosmesa6 installed successfully."

    # Export environment variables (may not persist after terminal restart)
    export PYOPENGL_PLATFORM=osmesa
    export MESA_GL_VERSION_OVERRIDE=3.3

    echo "Environment variables set. If they do not work, try running them manually."
else
    echo "Failed to install libosmesa6. Exiting."
    exit 1
fi