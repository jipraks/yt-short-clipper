#!/bin/bash
# Launch script for yt-short-clipper with proper environment

# Add local pip packages to PATH
export PATH="/home/mahdev/.local/bin:$PATH"

# Run the application
python3 app.py "$@"
