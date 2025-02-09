#!/bin/bash
#
# This script ensures that environment variables persist across terminal sessions.
#
# Usage:
# 1. Make the script executable: chmod +x persistent_exports.sh
# 2. Run it: ./persistent_exports.sh
#
# This script appends the necessary exports to ~/.bashrc so they load automatically 
# when opening a new terminal session. It also reloads the bash configuration
# immediately after to apply the changes.
#

# Append environment variables to ~/.bashrc to make them persistent
echo 'export PYOPENGL_PLATFORM=osmesa' >> ~/.bashrc
echo 'export MESA_GL_VERSION_OVERRIDE=3.3' >> ~/.bashrc

# Reload .bashrc so the changes take effect immediately
source ~/.bashrc

echo "Environment variables added to ~/.bashrc and applied."
echo "They will now persist in future terminal sessions."