#!/bin/bash

source .env
if [ -f ../.env ]; then
    source ../.env
fi

PARENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

PYTHON_INTERPRETER="/opt/homebrew/opt/python@3.11/libexec/bin/python"

# Check if a Python script was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <python_script.py> [additional_args...]"
    exit 1
fi

# Get absolute path of the Python script before changing directories
PYTHON_SCRIPT="$(realpath "$1")"
shift

cd "$(dirname "$0")"

$PYTHON_INTERPRETER "$PYTHON_SCRIPT" "$@"
