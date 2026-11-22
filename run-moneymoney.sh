#!/bin/sh
set -eu
TASK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$TASK_DIR"
exec "$TASK_DIR/.venv/bin/python" -m ing_investment.moneymoney_server "$@"
