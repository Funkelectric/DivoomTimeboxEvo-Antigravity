"""
macOS IOBluetooth RFCOMM Channel Client for Divoom Timebox-Evo.

Uses PyObjC to interface with macOS native IOBluetooth framework,
enumerating paired devices, opening an RFCOMM serial connection,
and pumping NSRunLoop so incoming device notifications (such as button presses)
are delivered to Python callbacks in real time.
"""

import time
from typing import Optional, Callable

try:
    import objc
    from Foundation import NSObject, NSRunLoop, NSDate
    import IOBluetooth
except ImportError:
    IOBluetooth = None
    NSRunLoop = None
    NSDate = None


class RFCOMMDelegate(NSObject):
    def init(self):
        self = objc.super(RFCOMMDelegate, self).init()
        if self is None:
            return None
        self.channel = None
        self.is_open = False
        self.on_data: Optional[Callable[[bytes], None]] = None
        return self

    def rfcommChannelOpenComplete_status_(self, channel, status):
        if status == 0:
            self.channel = channel
            self.is_open = True
            print("[Bluetooth] RFCOMM Channel opened successfully.", flush=True)
        else:
            print(f"[Bluetooth] Failed to open RFCOMM Channel. Status: {status}", flush=True)

    def rfcommChannelClosed_(self, channel):
        self.is_open = False
        print("[Bluetooth] RFCOMM Channel closed.", flush=True)

    def rfcommChannelData_data_length_(self, channel, data_ptr, length):
        try:
            if isinstance(data_ptr, (bytes, bytearray)):
                raw = bytes(data_ptr[:length])
            else:
                raw = bytes(data_ptr[:length])
        except Exception:
            raw = b""
        cb = getattr(self, "on_data", None)
        if cb and raw:
            try:
                cb(raw)
            except Exception as e:
                print(f"[Bluetooth] Callback error: {e}", flush=True)


class MacDivoomBluetooth:
    def __init__(self, device_name_substr: str = "Timebox-Evo"):
        self.device_name_substr = device_name_substr
        self.device = None
        self.channel = None
        self.delegate = None

    @staticmethod
    def list_paired_devices():
        if IOBluetooth is None:
            print("[Error] PyObjC IOBluetooth framework not loaded.", flush=True)
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
                print(f"[Bluetooth] Found target device: {d['name']} ({d['address']})", flush=True)
                return d["raw"]
        return None

    def connect(self, rfcomm_channel_id: int = 1) -> bool:
        """Connects to the Divoom Timebox-Evo RFCOMM channel (default channel 1)."""
        if IOBluetooth is None:
            print("[Error] IOBluetooth not available.", flush=True)
            return False

        self.device = self.find_device()
        if not self.device:
            print(f"[Bluetooth] No paired device matching '{self.device_name_substr}' found.", flush=True)
            return False

        self.delegate = RFCOMMDelegate.alloc().init()

        print(f"[Bluetooth] Opening RFCOMM channel {rfcomm_channel_id}...", flush=True)
        status, channel = self.device.openRFCOMMChannelSync_withChannelID_delegate_(
            None,
            rfcomm_channel_id,
            self.delegate,
        )

        # If a previous process died or macOS serial driver grabbed channel 1 (-536870212),
        # reset the baseband link once and retry.
        if status != 0 or channel is None:
            print(f"[Bluetooth] Initial open returned {status}; resetting stale link and retrying...", flush=True)
            try:
                if self.device.isConnected():
                    self.device.closeConnection()
                    time.sleep(1.5)
            except Exception:
                pass
            status, channel = self.device.openRFCOMMChannelSync_withChannelID_delegate_(
                None,
                rfcomm_channel_id,
                self.delegate,
            )

        if status == 0 and channel is not None:
            self.channel = channel
            print("[Bluetooth] Connected to Timebox-Evo RFCOMM channel!", flush=True)
            return True
        else:
            print(f"[Bluetooth] openRFCOMMChannelSync failed with status code: {status}", flush=True)
            return False

    def send_bytes(self, data: bytes) -> bool:
        if not self.channel or not self.channel.isOpen():
            print("[Bluetooth] Cannot send data: Channel is not open.", flush=True)
            return False
        status = self.channel.writeSync_length_(data, len(data))
        return status == 0

    def pump_events(self, duration: float = 0.05):
        """Pumps macOS NSRunLoop for `duration` seconds so RFCOMM incoming data callbacks fire."""
        if NSRunLoop is not None and NSDate is not None:
            NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(duration))
        else:
            time.sleep(duration)

    def close(self):
        if self.channel and self.channel.isOpen():
            self.channel.closeChannel()
            print("[Bluetooth] Channel closed.", flush=True)
        self.channel = None
