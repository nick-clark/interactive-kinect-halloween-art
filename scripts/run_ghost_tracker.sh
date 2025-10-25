#!/bin/bash

# Set library paths for libfreenect
export DYLD_LIBRARY_PATH="/Users/nick/kinect-v1-python-starter/libfreenect/build/lib:$DYLD_LIBRARY_PATH"
export LD_LIBRARY_PATH="/Users/nick/kinect-v1-python-starter/libfreenect/build/lib:$LD_LIBRARY_PATH"

# Change to project directory
cd /Users/nick/kinect-v1-python-starter

# Run the ghost tracker
python3 ghost_tracker_fixed.py
