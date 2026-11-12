"""
macOS IOBluetooth RFCOMM Channel Client for Divoom Timebox-Evo.

Uses PyObjC to interface with macOS native IOBluetooth framework,
enumerating paired devices and opening an RFCOMM serial connection.
"""

import sys
import time
from typing import Optional

try:
    import objc
    from Foundation import NSObject
    import IOBluetooth
except ImportError:
    IOBluetooth = None

class RFCOMMDelegate(NSObject):
    def init(self):
        self = objc.super(RFCOMMDelegate, self).init()
        if self is None:
            return None
        self.channel = None
        self.is_open = False
        return self

    def rfcommChannelOpenComplete_status_(self, channel, status):
        if status == 0:
            self.channel = channel
            self.is_open = True
            print("[Bluetooth] RFCOMM Channel opened successfully.")
        else:
            print(f"[Bluetooth] Failed to open RFCOMM Channel. Status: {status}")

    def rfcommChannelClosed_(self, channel):
        self.is_open = False
        print("[Bluetooth] RFCOMM Channel closed.")

    def rfcommChannelData_data_length_(self, channel, data_ptr, length):
        # Timebox-Evo status replies
        pass

class MacDivoomBluetooth:
    def __init__(self, device_name_substr: str = "Timebox-Evo"):
        self.device_name_substr = device_name_substr
        self.device = None
        self.channel = None
        self.delegate = None

    @staticmethod
    def list_paired_devices():
        if IOBluetooth is None:
            print("[Error] PyObjC IOBluetooth framework not loaded.")
            return []
        devices = IOBluetooth.IOBluetoothDevice.pairedDevices() or []
        info = []
        for dev in devices:
            name = dev.nameOrAddress() or "Unknown"
            addr = dev.addressString() or "00:00:00:00:00:00"
            connected = dev.isConnected()
            info.append({"name": str(name), "address": str(addr), "connected": bool(connected), "raw": dev})
        return info

    def find_device(self):
        devices = self.list_paired_devices()
        for d in devices:
            if self.device_name_substr.lower() in d["name"].lower():
                print(f"[Bluetooth] Found target device: {d['name']} ({d['address']})")
                return d["raw"]
        return None

    def connect(self, rfcomm_channel_id: int = 1) -> bool:
        """Connects to the Divoom Timebox-Evo RFCOMM channel (default channel 1)."""
        if IOBluetooth is None:
            print("[Error] IOBluetooth not available.")
            return False

        self.device = self.find_device()
        if not self.device:
            print(f"[Bluetooth] No paired device matching '{self.device_name_substr}' found.")
            print("[Hint] Pair the Timebox-Evo first in macOS System Settings > Bluetooth.")
            return False

        self.delegate = RFCOMMDelegate.alloc().init()

        # Open RFCOMM channel synchronously or asynchronously
        print(f"[Bluetooth] Opening RFCOMM channel {rfcomm_channel_id}...")
        status, channel = self.device.openRFCOMMChannelSync_withChannelID_delegate_(
            None,
            rfcomm_channel_id,
            self.delegate
        )

        if status == 0 and channel is not None:
            self.channel = channel
            print("[Bluetooth] Connected to Timebox-Evo RFCOMM channel!")
            return True
        else:
            print(f"[Bluetooth] openRFCOMMChannelSync failed with status code: {status}")
            return False

    def send_bytes(self, data: bytes) -> bool:
        if not self.channel or not self.channel.isOpen():
            print("[Bluetooth] Cannot send data: Channel is not open.")
            return False
        
        status = self.channel.writeSync_length_(data, len(data))
        return status == 0

    def close(self):
        if self.channel and self.channel.isOpen():
            self.channel.closeChannel()
            print("[Bluetooth] Channel closed.")
        self.channel = None

if __name__ == "__main__":
    print("Scanning macOS paired Bluetooth devices:")
    devices = MacDivoomBluetooth.list_paired_devices()
    if not devices:
        print("No paired Bluetooth devices detected.")
    else:
        for idx, dev in enumerate(devices):
            print(f" {idx + 1}. {dev['name']} [{dev['address']}] (Connected: {dev['connected']})")
