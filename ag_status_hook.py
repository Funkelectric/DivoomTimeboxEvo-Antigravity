#!/usr/bin/env python3
"""
Antigravity State Helper Hook.

Writes agent status to ~/.antigravity/state.json for consumption by the Divoom daemon.
Usage:
    python3 ag_status_hook.py --state thinking
    python3 ag_status_hook.py --state running_tool --tool run_command
    python3 ag_status_hook.py --state success
    python3 ag_status_hook.py --state idle
"""

import os
import sys
import json
import time
import argparse

DEFAULT_STATE_PATH = os.path.expanduser("/Users/Opencode/FIRMWARE/DIVOO/state.json")

def write_state(state: str, tool_name: str = "", details: str = "", path: str = DEFAULT_STATE_PATH):
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    payload = {
        "state": state,
        "tool": tool_name,
        "details": details,
        "timestamp": int(time.time()),
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    # Write atomically
    temp_path = f"{path}.tmp.{os.getpid()}"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(temp_path, path)
    print(f"[State Hook] Updated state to '{state}' at {path}")

def main():
    parser = argparse.ArgumentParser(description="Antigravity State Hook")
    parser.add_argument("--state", type=str, required=True, 
                        choices=["idle", "thinking", "planning", "running_tool", "waiting_user", "success", "error"],
                        help="Current status")
    parser.add_argument("--tool", type=str, default="", help="Tool name if running_tool")
    parser.add_argument("--details", type=str, default="", help="Optional summary/detail text")
    parser.add_argument("--path", type=str, default=DEFAULT_STATE_PATH, help="Path to state.json")

    args = parser.parse_args()
    write_state(args.state, args.tool, args.details, args.path)

if __name__ == "__main__":
    main()
