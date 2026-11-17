#!/bin/zsh
set -e
TASK_ROOT=${0:A:h}
cd "$TASK_ROOT"
exec /usr/bin/python3 "$TASK_ROOT/bootstrap_setup.py" "$@"
