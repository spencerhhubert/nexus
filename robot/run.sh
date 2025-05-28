#!/bin/bash

source .env
source ../.env

PARENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

PYTHON_INTERPRETER="/opt/homebrew/opt/python@3.11/libexec/bin/python"

# Run the Python script
cd "$(dirname "$0")"
$PYTHON_INTERPRETER main.py "$@"
