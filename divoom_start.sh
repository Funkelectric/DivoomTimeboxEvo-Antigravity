#!/bin/zsh
# Start the Divoom status daemon in the background.
cd "$(dirname "$0")" || exit 1
PID_FILE=.daemon.pid
LOG_FILE=daemon.log

if [[ -f $PID_FILE ]] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
  echo "Daemon already running (PID $(cat $PID_FILE))"
  exit 0
fi

nohup .venv/bin/python divoom_daemon.py "$@" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Daemon started (PID $!). Log: $PWD/$LOG_FILE"
