#!/bin/zsh
# Stop the Divoom status daemon cleanly (works both inside and outside sandbox).
cd "$(dirname "$0")" || exit 1
PID_FILE=.daemon.pid
STOP_FILE=.daemon.stop

touch "$STOP_FILE"

if [[ -f $PID_FILE ]]; then
  PID=$(cat "$PID_FILE")
  kill -TERM "$PID" 2>/dev/null
  echo "Stopping daemon (PID $PID)..."
  rm -f "$PID_FILE"
else
  echo "Stop signal written."
fi
sleep 0.6
rm -f "$STOP_FILE"
