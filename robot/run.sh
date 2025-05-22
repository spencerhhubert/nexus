#!/bin/bash

# Get the absolute path to the parent directory of the robot package
PARENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Add parent directory to PYTHONPATH
export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

# Set environment variables
export DEBUG="${DEBUG:-1}"
export MC_PATH="${MC_PATH:-/dev/ttyACM0}"

# Print debug info
echo "PYTHONPATH: $PYTHONPATH"
echo "DEBUG level: $DEBUG"
echo "MC_PATH: $MC_PATH"

# Use specific Python interpreter
PYTHON_INTERPRETER="/opt/homebrew/opt/python@3.11/libexec/bin/python"

# Run the Python script
cd "$(dirname "$0")"
$PYTHON_INTERPRETER main.py