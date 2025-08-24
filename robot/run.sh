#!/bin/bash

source .env

PARENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

PYTHON_INTERPRETER="/opt/homebrew/opt/python@3.11/libexec/bin/python"

cd "$(dirname "$0")"

# Check if --dump argument is present
if [[ " $* " == *" --dump "* ]]; then
    # Remove --dump from arguments
    args=()
    for arg in "$@"; do
        if [[ "$arg" != "--dump" ]]; then
            args+=("$arg")
        fi
    done

    mkdir -p ../logs
    TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
    $PYTHON_INTERPRETER main.py "${args[@]}" &> "../logs/${TIMESTAMP}.log"
else
    $PYTHON_INTERPRETER main.py "$@"
fi
