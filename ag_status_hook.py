#!/usr/bin/env python3
"""
Antigravity State & Interactive Question Helper Hook.

Writes agent status to /Users/Opencode/FIRMWARE/DIVOO/state.json for consumption by the Divoom daemon,
and supports asking a Yes/No question that waits for the user to press the physical Play (Yes) or
Light (No) button on top of the Timebox-Evo.

Usage:
    python3 ag_status_hook.py --state thinking
    python3 ag_status_hook.py --state running_tool --tool run_command
    python3 ag_status_hook.py --state waiting_user --details "Deploy to prod?" --wait-answer --timeout 60
    python3 ag_status_hook.py --state success
    python3 ag_status_hook.py --state idle
"""

import os
import sys
import json
import time
import argparse

BASE_DIR = "/Users/Opencode/FIRMWARE/DIVOO"
DEFAULT_STATE_PATH = os.path.join(BASE_DIR, "state.json")
DEFAULT_ANSWER_PATH = os.path.join(BASE_DIR, "answer.json")


def write_state(state: str, tool_name: str = "", details: str = "", path: str = DEFAULT_STATE_PATH) -> int:
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    ts = int(time.time())
    payload = {
        "state": state,
        "tool": tool_name,
        "details": details,
        "timestamp": ts,
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
    }

    temp_path = f"{path}.tmp.{os.getpid()}"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(temp_path, path)
    print(f"[State Hook] Updated state to '{state}' at {path}", flush=True)
    return ts


def wait_for_button_answer(since_ts: float, answer_path: str = DEFAULT_ANSWER_PATH, timeout: float = 60.0) -> str:
    """Polls answer.json for a fresh button press after `since_ts`."""
    # Remove any stale answer file before waiting
    if os.path.exists(answer_path):
        try:
            os.remove(answer_path)
        except Exception:
            pass

    print(f"[State Hook] Waiting up to {int(timeout)}s for Timebox-Evo button (Play=YES, Light=NO)...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(answer_path):
            try:
                with open(answer_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ans = data.get("answer")
                btn = data.get("button", "")
                if ans in ("yes", "no", "timeout"):
                    print(f"[State Hook] Received answer='{ans}' (button='{btn}')", flush=True)
                    return ans
            except Exception:
                pass
        time.sleep(0.25)

    print("[State Hook] Timed out waiting for button press.", flush=True)
    return "timeout"


def main():
    parser = argparse.ArgumentParser(description="Antigravity State Hook")
    parser.add_argument(
        "--state",
        type=str,
        required=True,
        choices=["idle", "thinking", "planning", "running_tool", "waiting_user", "success", "error"],
        help="Current status",
    )
    parser.add_argument("--tool", type=str, default="", help="Tool name if running_tool")
    parser.add_argument("--details", type=str, default="", help="Optional summary/question text")
    parser.add_argument("--path", type=str, default=DEFAULT_STATE_PATH, help="Path to state.json")
    parser.add_argument("--answer-path", type=str, default=DEFAULT_ANSWER_PATH, help="Path to answer.json")
    parser.add_argument("--wait-answer", action="store_true", help="Wait for Play(Yes)/Light(No) button press")
    parser.add_argument("--timeout", type=float, default=60.0, help="Seconds to wait when --wait-answer is set")

    args = parser.parse_args()
    since_ts = time.time()
    write_state(args.state, args.tool, args.details, args.path)

    if args.wait_answer:
        ans = wait_for_button_answer(since_ts=since_ts, answer_path=args.answer_path, timeout=args.timeout)
        print(f"ANSWER={ans}", flush=True)


if __name__ == "__main__":
    main()
