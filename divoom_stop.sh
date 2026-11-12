#!/bin/zsh
# Stop the Divoom status daemon.
cd "$(dirname "$0")" || exit 1
PID_FILE=.daemon.pid

if [[ ! -f $PID_FILE ]]; then
  echo "Daemon not running (no PID file)"
  exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
  kill -TERM "$PID"
  echo "Daemon stopped (PID $PID)"
else
  echo "Daemon was not running (stale PID $PID)"
fi
rm -f "$PID_FILE"
