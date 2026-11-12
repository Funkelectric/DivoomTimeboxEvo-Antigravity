#!/usr/bin/env python3
"""
Divoom Timebox-Evo Antigravity Status Daemon.

Monitors ~/.antigravity/state.json and renders corresponding animated
pixel art (16x16) to the Divoom Timebox-Evo over Bluetooth.
"""

import os
import sys
import time
import json
import signal
import argparse
from typing import Optional

from divoom_protocol import encode_static_image, encode_brightness, encode_channel
from pixel_assets import get_frames_for_state
from divoom_connection import DivoomConnection

DEFAULT_STATE_PATH = os.path.expanduser("/Users/Opencode/FIRMWARE/DIVOO/state.json")

class DivoomStatusDaemon:
    def __init__(self, state_path: str = DEFAULT_STATE_PATH, fps: float = 2.0, port: Optional[str] = None):
        self.state_path = state_path
        self.frame_delay = 1.0 / max(0.5, fps)
        self.conn = DivoomConnection(port_name=port)
        self.running = False
        self.current_state = "idle"
        self.frame_idx = 0
        self.last_mtime = 0.0

    def read_current_state(self) -> str:
        if not os.path.exists(self.state_path):
            return "idle"
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("state", "idle")
        except Exception:
            return self.current_state

    def run(self, dry_run: bool = False):
        self.running = True
        print(f"[Daemon] Starting Antigravity Divoom Daemon...")
        print(f"[Daemon] Watching: {self.state_path}")

        if not dry_run:
            connected = self.conn.connect()
            if not connected:
                print("[Daemon] Could not connect to Bluetooth device. Running in preview mode.")
                dry_run = True
            else:
                # Set initial brightness
                self.conn.send_bytes(encode_brightness(100)); self.conn.send_bytes(encode_channel(5))

        def signal_handler(sig, frame):
            print("\n[Daemon] Stopping...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while self.running:
            new_state = self.read_current_state()
            if new_state != self.current_state:
                print(f"[Daemon] State transitioned: {self.current_state} -> {new_state}")
                self.current_state = new_state
                self.frame_idx = 0

            frames = get_frames_for_state(self.current_state)
            if not frames:
                time.sleep(self.frame_delay)
                continue

            frame = frames[self.frame_idx % len(frames)]
            self.frame_idx += 1

            if not dry_run:
                try:
                    packet = encode_static_image(frame)
                    self.conn.send_bytes(packet)
                except Exception as e:
                    print(f"[Daemon] Send error: {e}")
            else:
                print(f"\r[Preview] State: {self.current_state:<12} (Frame {self.frame_idx % len(frames) + 1}/{len(frames)})", end="", flush=True)

            time.sleep(self.frame_delay)

        if not dry_run:
            self.conn.close()
        print("\n[Daemon] Stopped.")

    def test_cycle_states(self, dry_run: bool = False):
        """Cycles through every supported state for visual verification."""
        states = ["idle", "thinking", "running_tool", "waiting_user", "success", "error"]
        print(f"[Daemon] Testing state animations on Divoom...")
        if not dry_run:
            if not self.conn.connect():
                print("[Daemon] Bluetooth connection failed. Switching to preview mode.")
                dry_run = True
            else:
                self.conn.send_bytes(encode_brightness(100)); self.conn.send_bytes(encode_channel(5))

        for state in states:
            print(f"\n--- Demonstrating State: {state.upper()} ---")
            frames = get_frames_for_state(state)
            for cycle in range(3):  # 3 animation loops per state
                for idx, frame in enumerate(frames):
                    if not dry_run:
                        packet = encode_static_image(frame)
                        self.conn.send_bytes(packet)
                    else:
                        print(f"\r[{state}] Frame {idx + 1}/{len(frames)}", end="", flush=True)
                    time.sleep(self.frame_delay)

        if not dry_run:
            self.conn.close()
        print("\n[Daemon] State test cycle finished.")

def main():
    parser = argparse.ArgumentParser(description="Antigravity Divoom Status Daemon")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending Bluetooth packets")
    parser.add_argument("--test-states", action="store_true", help="Cycle through all animation states")
    parser.add_argument("--fps", type=float, default=2.5, help="Animation frames per second")
    parser.add_argument("--port", type=str, default=None, help="Specific serial port (e.g. /dev/cu.TimeBox-Evo-audio)")
    parser.add_argument("--state-file", type=str, default=DEFAULT_STATE_PATH, help="Path to state.json")

    args = parser.parse_args()
    daemon = DivoomStatusDaemon(state_path=args.state_file, fps=args.fps, port=args.port)

    if args.test_states:
        daemon.test_cycle_states(dry_run=args.dry_run)
    else:
        daemon.run(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
