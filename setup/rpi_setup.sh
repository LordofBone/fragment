#!/bin/bash

# Update package lists
sudo apt-get update && sudo apt-get install -y libosmesa6

# Check if libosmesa6 installed successfully
if dpkg -l | grep -q libosmesa6; then
    echo "libosmesa6 installed successfully."
    
    # Export environment variables
    export PYOPENGL_PLATFORM=osmesa
    export MESA_GL_VERSION_OVERRIDE=3.3

    echo "Environment variables set."
else
    echo "Failed to install libosmesa6. Exiting."
    exit 1
fi