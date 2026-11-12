"""
macOS Bluetooth Connection Manager for Divoom Timebox-Evo.

Architecture discovered from APK & hardware testing:
1. Primary (Bidirectional SPP/RFCOMM via IOBluetooth):
   - Sends 16x16 frames, channel lock (0x45 05), and alarm chime preview (0xA5)
   - Receives device ACKs and physical button press packets (Play / Light) via
     RFCOMMDelegate when `pump_events()` spins `NSRunLoop`.
2. Optional BLE Notify Listener (`bleak`):
   - Can also subscribe to 49535343-1e4d-4bd9-ba61-23c647249616 when BLE-only
     monitoring is desired.
"""

import glob
import time
from typing import Optional, Callable

try:
    import serial
except ImportError:
    serial = None

from mac_bluetooth import MacDivoomBluetooth


class DivoomConnection:
    def __init__(
        self,
        port_name: Optional[str] = None,
        on_notify: Optional[Callable[[bytes], None]] = None,
    ):
        self.port_name = port_name
        self.on_notify = on_notify
        self.bt: Optional[MacDivoomBluetooth] = None
        self.ser = None
        self.mode: str = "disconnected"

    @staticmethod
    def find_serial_port() -> Optional[str]:
        candidates = glob.glob("/dev/cu.*Time[bB]ox*") + glob.glob("/dev/cu.*Divoom*")
        if candidates:
            return sorted(candidates)[0]
        return None

    def set_notify_callback(self, callback: Callable[[bytes], None]):
        self.on_notify = callback
        if self.bt and self.bt.delegate:
            self.bt.delegate.on_data = callback

    def connect(self) -> bool:
        # 1. Primary: Native macOS IOBluetooth RFCOMM Channel 1 (full bidirectional TX + RX)
        if not self.port_name:
            self.bt = MacDivoomBluetooth()
            if self.bt.connect():
                if self.bt.delegate and self.on_notify:
                    self.bt.delegate.on_data = self.on_notify
                self.mode = "rfcomm"
                return True
            self.bt = None

        # 2. Secondary: Explicit serial port if requested
        port = self.port_name or self.find_serial_port()
        if port and serial is not None:
            try:
                print(f"[Connection] Connecting to serial port {port}...", flush=True)
                self.ser = serial.Serial(port, baudrate=115200, timeout=0.02, write_timeout=1.0)
                self.mode = "serial"
                print(f"[Connection] Connected via {port}!", flush=True)
                return True
            except Exception as e:
                print(f"[Connection] Serial connect failed: {e}", flush=True)
                self.ser = None

        return False

    def send_bytes(self, data: bytes) -> bool:
        if self.bt:
            return self.bt.send_bytes(data)
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(data)
                self.ser.flush()
                return True
            except Exception as e:
                print(f"[Connection] Serial write error: {e}", flush=True)
                return False
        return False

    def sleep_and_pump(self, duration: float):
        """Sleeps for `duration` seconds while pumping incoming Bluetooth notifications."""
        if self.bt:
            end_t = time.time() + duration
            while time.time() < end_t:
                rem = max(0.01, min(0.05, end_t - time.time()))
                self.bt.pump_events(rem)
        elif self.ser and self.ser.is_open:
            end_t = time.time() + duration
            while time.time() < end_t:
                try:
                    rx = self.ser.read(128)
                    if rx and self.on_notify:
                        self.on_notify(rx)
                except Exception:
                    pass
                time.sleep(0.03)
        else:
            time.sleep(duration)

    def close(self):
        if self.bt:
            self.bt.close()
            self.bt = None
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        self.mode = "disconnected"
        print("[Connection] Disconnected.", flush=True)
