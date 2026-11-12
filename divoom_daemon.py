#!/usr/bin/env python3
"""
Divoom Timebox-Evo Antigravity Status Daemon (Bidirectional RFCOMM + Yes/No Buttons + Native Chime).

Monitors state.json and renders corresponding animated pixel art (16x16) to the
Divoom Timebox-Evo over macOS IOBluetooth RFCOMM.

Key behaviors:
- Suppresses default Timebox button side effects while the daemon is active:
  * If the Light button is pressed at any time, the device's built-in mode change
    is immediately overridden with `encode_channel(5)` + the active Antigravity frame.
- When entering `waiting_user` state:
  * Plays a short native chime on the Timebox-Evo (`SPP_SET_ALARM_LISTEN` mode=3)
  * Listens for physical button presses on the top of the Timebox-Evo:
    - Play button  -> answers "yes"
    - Light button -> answers "no"
  * Writes the response atomically to `answer.json` and flashes `success` (green check)
    or `error` (red !) for visual confirmation before returning to `idle`.
"""

import os
import sys
import time
import json
import signal
import argparse
import threading
from typing import Optional

from divoom_protocol import (
    encode_static_image,
    encode_brightness,
    encode_channel,
    encode_alarm_preview,
    parse_button_notification,
)
from pixel_assets import get_frames_for_state
from divoom_connection import DivoomConnection

BASE_DIR = "/Users/Opencode/FIRMWARE/DIVOO"
DEFAULT_STATE_PATH = os.path.join(BASE_DIR, "state.json")
DEFAULT_ANSWER_PATH = os.path.join(BASE_DIR, "answer.json")
DEFAULT_CONTROL_PATH = os.path.join(BASE_DIR, ".daemon.stop")


class DivoomStatusDaemon:
    def __init__(
        self,
        state_path: str = DEFAULT_STATE_PATH,
        answer_path: str = DEFAULT_ANSWER_PATH,
        fps: float = 2.5,
        port: Optional[str] = None,
        question_timeout: float = 60.0,
    ):
        self.state_path = state_path
        self.answer_path = answer_path
        self.frame_delay = 1.0 / max(0.5, fps)
        self.question_timeout = question_timeout
        self.conn = DivoomConnection(
            port_name=port,
            on_notify=self._on_device_notify,
        )
        self.running = False
        self.current_state = "idle"
        self.frame_idx = 0
        self.waiting_since: Optional[float] = None
        self._pending_button: Optional[str] = None
        self._ignore_notify_until: float = 0.0
        self._channel_lock_sent_at: float = 0.0
        self._expect_channel_echo: bool = False
        self._lock = threading.Lock()

    def _send_channel_lock(self):
        self._channel_lock_sent_at = time.time()
        self._expect_channel_echo = True
        self.conn.send_bytes(encode_channel(5))

    def _on_device_notify(self, data: bytes):
        now = time.time()
        if now < self._ignore_notify_until:
            return
        btn = parse_button_notification(data)
        if not btn:
            return
        # Sending encode_channel(5) or stopping the alarm chime causes the Timebox-Evo
        # firmware to emit a single `bd 55 13 01 1e` (value=0x1e) echo ~1.5-4.5s later.
        # Real Play button presses toggle the value byte (`data[8]`) to 0x32 (50) or
        # send a second 0x1e press. Ignore only the first automatic `0x1e` echo!
        if btn == "yes" and len(data) >= 9 and data[6] == 0x13 and data[8] == 0x1E and self._expect_channel_echo and (now - self._channel_lock_sent_at) < 5.5:
            self._expect_channel_echo = False
            print(f"[BT RX] (ignored channel-lock echo) {data.hex(' ')}", flush=True)
            return
        print(f"[BT RX] {data.hex(' ')} -> button={btn} (state={self.current_state})", flush=True)
        with self._lock:
            # If Light button was pressed ("no"), immediately re-lock Custom Channel 5
            # and redraw the current Antigravity frame so the default animation never takes over
            if btn == "no":
                try:
                    self._send_channel_lock()
                    frames = get_frames_for_state(self.current_state)
                    if frames:
                        cur_frame = frames[self.frame_idx % len(frames)]
                        self.conn.send_bytes(encode_static_image(cur_frame))
                except Exception:
                    pass
            if self.current_state == "waiting_user":
                self._pending_button = btn

    def read_current_state(self) -> dict:
        if not os.path.exists(self.state_path):
            return {"state": "idle"}
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {"state": self.current_state}

    def write_state_file(self, state: str, details: str = ""):
        payload = {
            "state": state,
            "tool": "",
            "details": details,
            "timestamp": int(time.time()),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        tmp = f"{self.state_path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, self.state_path)

    def write_answer_file(self, answer: str, button: str, question: str = ""):
        payload = {
            "answer": answer,
            "button": button,
            "question": question,
            "timestamp": int(time.time()),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        tmp = f"{self.answer_path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, self.answer_path)
        print(f"[Daemon] Wrote answer='{answer}' (button={button}) to {self.answer_path}", flush=True)

    def play_question_chime(self):
        """Triggers a short native chime on the Timebox-Evo using SPP_SET_ALARM_LISTEN (mode=3)."""
        try:
            print("[Daemon] Triggering Timebox-Evo native question chime...", flush=True)
            # Suppress all incoming packets during the chime + 1.0s after stopping it,
            # because stopping the alarm preview causes the Timebox to emit a delayed
            # `bd 55 13 01 1e` packet (the exact same packet as the Play button!).
            self._ignore_notify_until = time.time() + 2.5
            q_frames = get_frames_for_state("waiting_user")
            if q_frames:
                self.conn.send_bytes(encode_static_image(q_frames[0]))
            self.conn.send_bytes(encode_alarm_preview(True, mode=3, volume=60))
            self.conn.sleep_and_pump(0.65)
            self.conn.send_bytes(encode_alarm_preview(False, mode=0, volume=0))
            # Stopping the alarm preview causes the Timebox-Evo firmware to emit a delayed
            # `bd 55 13 01 1e` packet ~2-5s later; arm _expect_channel_echo to filter that 1 echo.
            self._channel_lock_sent_at = time.time()
            self._expect_channel_echo = True
            if q_frames:
                self.conn.send_bytes(encode_static_image(q_frames[0]))
            self._ignore_notify_until = time.time() + 0.15
            with self._lock:
                self._pending_button = None
        except Exception as e:
            print(f"[Daemon] Chime error: {e}", flush=True)

    def flash_feedback(self, state_name: str, duration: float = 1.4):
        frames = get_frames_for_state(state_name)
        end_t = time.time() + duration
        idx = 0
        self._ignore_notify_until = end_t + 0.2
        while time.time() < end_t and self.running:
            frame = frames[idx % len(frames)]
            idx += 1
            self.conn.send_bytes(encode_static_image(frame))
            self.conn.sleep_and_pump(0.35)

    def run(self, dry_run: bool = False):
        self.running = True
        print("[Daemon] Starting Antigravity Divoom Daemon...", flush=True)
        print(f"[Daemon] Watching state:  {self.state_path}", flush=True)
        print(f"[Daemon] Answer output:   {self.answer_path}", flush=True)

        if not dry_run:
            connected = self.conn.connect()
            if not connected:
                print("[Daemon] Could not connect to Bluetooth device. Running in preview mode.", flush=True)
                dry_run = True
            else:
                print(f"[Daemon] Active transport mode: {self.conn.mode.upper()}", flush=True)
                self._ignore_notify_until = time.time() + 0.5
                self.conn.send_bytes(encode_brightness(100))
                self._send_channel_lock()

        def signal_handler(sig, frame):
            print("\n[Daemon] Stopping...", flush=True)
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        if os.path.exists(DEFAULT_CONTROL_PATH):
            try:
                os.remove(DEFAULT_CONTROL_PATH)
            except Exception:
                pass

        while self.running:
            if os.path.exists(DEFAULT_CONTROL_PATH):
                print("\n[Daemon] Stop file detected, shutting down cleanly...", flush=True)
                try:
                    os.remove(DEFAULT_CONTROL_PATH)
                except Exception:
                    pass
                break
            state_doc = self.read_current_state()
            new_state = state_doc.get("state", "idle")
            question_text = state_doc.get("details", "")

            if new_state != self.current_state:
                print(f"[Daemon] State transitioned: {self.current_state} -> {new_state}", flush=True)
                self.current_state = new_state
                self.frame_idx = 0
                with self._lock:
                    self._pending_button = None
                if new_state == "waiting_user":
                    self.waiting_since = time.time()
                    if not dry_run:
                        self.play_question_chime()
                else:
                    self.waiting_since = None

            # Check for button answer or timeout while in waiting_user
            if self.current_state == "waiting_user":
                with self._lock:
                    btn = self._pending_button
                    self._pending_button = None

                if btn in ("yes", "no"):
                    btn_name = "play" if btn == "yes" else "light"
                    self.write_answer_file(answer=btn, button=btn_name, question=question_text)
                    if not dry_run:
                        self._send_channel_lock()
                        self.flash_feedback("success" if btn == "yes" else "error", duration=1.4)
                    self.write_state_file("idle", details=f"Answered {btn} via {btn_name} button")
                    self.current_state = "idle"
                    self.waiting_since = None
                    continue

                if self.waiting_since and (time.time() - self.waiting_since) > self.question_timeout:
                    print("[Daemon] Question waiting_user timed out (60s). Returning to idle.", flush=True)
                    self.write_answer_file(answer="timeout", button="none", question=question_text)
                    self.write_state_file("idle", details="Question timed out")
                    self.current_state = "idle"
                    self.waiting_since = None
                    continue

            frames = get_frames_for_state(self.current_state)
            if not frames:
                self.conn.sleep_and_pump(self.frame_delay)
                continue

            frame = frames[self.frame_idx % len(frames)]
            self.frame_idx += 1

            if not dry_run:
                try:
                    if not self.conn.bt or not self.conn.bt.channel or not self.conn.bt.channel.isOpen():
                        print("[Daemon] Bluetooth link lost; reconnecting...", flush=True)
                        if self.conn.connect():
                            self._ignore_notify_until = time.time() + 0.5
                            self.conn.send_bytes(encode_brightness(100))
                            self._send_channel_lock()
                    packet = encode_static_image(frame)
                    self.conn.send_bytes(packet)
                except Exception as e:
                    print(f"[Daemon] Send error: {e}", flush=True)
            else:
                print(
                    f"\r[Preview] State: {self.current_state:<12} (Frame {self.frame_idx % len(frames) + 1}/{len(frames)})",
                    end="",
                    flush=True,
                )

            self.conn.sleep_and_pump(self.frame_delay)

        if not dry_run:
            self.conn.close()
        print("\n[Daemon] Stopped.", flush=True)

    def test_cycle_states(self, dry_run: bool = False):
        """Cycles through every supported state for visual verification."""
        states = ["idle", "thinking", "running_tool", "waiting_user", "success", "error"]
        print("[Daemon] Testing state animations on Divoom...", flush=True)
        if not dry_run:
            if not self.conn.connect():
                print("[Daemon] Bluetooth connection failed. Switching to preview mode.", flush=True)
                dry_run = True
            else:
                print(f"[Daemon] Active transport mode: {self.conn.mode.upper()}", flush=True)
                self.conn.send_bytes(encode_brightness(100))
                self.conn.send_bytes(encode_channel(5))

        for state in states:
            print(f"\n--- Demonstrating State: {state.upper()} ---", flush=True)
            frames = get_frames_for_state(state)
            for _ in range(3):
                for idx, frame in enumerate(frames):
                    if not dry_run:
                        packet = encode_static_image(frame)
                        self.conn.send_bytes(packet)
                    else:
                        print(f"\r[{state}] Frame {idx + 1}/{len(frames)}", end="", flush=True)
                    self.conn.sleep_and_pump(self.frame_delay)

        if not dry_run:
            self.conn.close()
        print("\n[Daemon] State test cycle finished.", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Antigravity Divoom Status Daemon")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending Bluetooth packets")
    parser.add_argument("--test-states", action="store_true", help="Cycle through all animation states")
    parser.add_argument("--fps", type=float, default=2.5, help="Animation frames per second")
    parser.add_argument("--port", type=str, default=None, help="Specific serial port")
    parser.add_argument("--state-file", type=str, default=DEFAULT_STATE_PATH, help="Path to state.json")
    parser.add_argument("--answer-file", type=str, default=DEFAULT_ANSWER_PATH, help="Path to answer.json")
    parser.add_argument("--timeout", type=float, default=60.0, help="Timeout in seconds for waiting_user button answer")

    args = parser.parse_args()
    daemon = DivoomStatusDaemon(
        state_path=args.state_file,
        answer_path=args.answer_file,
        fps=args.fps,
        port=args.port,
        question_timeout=args.timeout,
    )

    if args.test_states:
        daemon.test_cycle_states(dry_run=args.dry_run)
    else:
        daemon.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
