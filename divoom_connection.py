"""
macOS Serial / RFCOMM Connection Manager for Divoom Timebox-Evo.

Supports:
1. Native macOS virtual serial device (/dev/cu.TimeBox-Evo-audio or /dev/cu.TimeBox-Evo)
2. PyObjC IOBluetooth RFCOMM fallback
"""

import os
import glob
import time
from typing import Optional

try:
    import serial
except ImportError:
    serial = None

from mac_bluetooth import MacDivoomBluetooth

class DivoomConnection:
    def __init__(self, port_name: Optional[str] = None):
        self.port_name = port_name
        self.ser = None
        self.bt_fallback = None

    @staticmethod
    def find_serial_port() -> Optional[str]:
        """Finds macOS Bluetooth serial tty/cu device for Timebox-Evo."""
        candidates = glob.glob("/dev/cu.*Time[bB]ox*") + glob.glob("/dev/cu.*Divoom*")
        if candidates:
            return sorted(candidates)[0]
        return None

    def connect(self) -> bool:
        port = self.port_name or self.find_serial_port()
        if port and serial is not None:
            try:
                print(f"[Connection] Connecting to serial port {port}...")
                self.ser = serial.Serial(port, baudrate=115200, timeout=1.0)
                print(f"[Connection] Connected via {port}!")
                return True
            except Exception as e:
                print(f"[Connection] Serial connect failed: {e}")
                self.ser = None

        # Fallback to IOBluetooth RFCOMM
        print("[Connection] Falling back to IOBluetooth RFCOMM...")
        self.bt_fallback = MacDivoomBluetooth()
        return self.bt_fallback.connect()

    def send_bytes(self, data: bytes) -> bool:
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(data)
                self.ser.flush()
                return True
            except Exception as e:
                print(f"[Connection] Serial write error: {e}")
                return False
        elif self.bt_fallback:
            return self.bt_fallback.send_bytes(data)
        return False

    def close(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        if self.bt_fallback:
            self.bt_fallback.close()
            self.bt_fallback = None
        print("[Connection] Disconnected.")
