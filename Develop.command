#!/bin/zsh
TASK_ROOT=${0:A:h}
cd "$TASK_ROOT"
"$TASK_ROOT/dev"
RESULT=$?
read "?Press Enter to close this window."
exit $RESULT
