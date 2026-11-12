# Divoom Timebox-Evo Antigravity Integration: Status & Next Steps

This document summarizes the current technical status, discovered hardware details, reverse-engineered APK protocol findings, and prioritized next steps to control the **Divoom Timebox-Evo** from macOS.

---

## 1. Executive Summary & Current State

- **Goal**: Connect Divoom Timebox-Evo (16x16 RGB LED screen) directly to macOS via Bluetooth to display real-time animated Antigravity status states (Thinking, Running Tool, Waiting for User, Success, Error, Idle).
- **Environment**: macOS with local Python virtual environment (`/Users/Opencode/FIRMWARE/DIVOO/.venv`) equipped with `bleak`, `pyserial`, `pyobjc-framework-IOBluetooth`, and `Pillow`.
- **Status Hook & Watcher**:
  - Implemented in [ag_status_hook.py](file:///Users/Opencode/FIRMWARE/DIVOO/ag_status_hook.py) and [divoom_daemon.py](file:///Users/Opencode/FIRMWARE/DIVOO/divoom_daemon.py).
  - Watches `/Users/Opencode/FIRMWARE/DIVOO/state.json`.
- **Pixel Art Engine**:
  - Multi-frame 16x16 animations handcrafted in [pixel_assets.py](file:///Users/Opencode/FIRMWARE/DIVOO/pixel_assets.py) with full color palette definitions.

---

## 2. Reverse-Engineering & Hardware Findings

### Dual-Bluetooth Architecture
The Divoom Timebox-Evo operates with a split architecture:
1. **Bluetooth Classic Audio Sink (`TimeBox-Evo-audio` / `11:75:58:A4:FA:0C`)**:
   - macOS provisions `/dev/cu.TimeBox-Evo-audio` upon pairing.
   - Used for A2DP music and macOS system sound output.
   - Large raw uncompressed 780-byte frame writes across this virtual serial device cause buffer timeouts.
2. **Bluetooth Low Energy (BLE) Transparent UART (`TimeBox-Evo-audio` / `D2067D20-7909-489F-615A-0C778CF92D8D`)**:
   - Device information read directly:
     - **Model Number**: `105xE` (TimeBox-Evo)
     - **MCU**: Anyka (Firmware `0.0.0.2`, Software `0.0.0.3`)
   - Uses **Microchip/ISSC Transparent UART Service**:
     - **Service UUID**: `49535343-fe7d-4ae5-8fa9-9fafd205e455`
     - **Config Char**: `49535343-6daa-4d02-abf6-19569aca69fe` (Reads `535050` = ASCII `"SPP"`)
     - **Write Char (TX)**: `49535343-8841-43f4-a8d4-ecbe34729bb3` (Write without response / Write)
     - **Notify Char (RX)**: `49535343-1e4d-4bd9-ba61-23c647249616` (Notify)

### Handshake Behavior Discovered
- Connecting to the BLE GATT service wakes up the display, transitions from **Clock -> Bluetooth Icon -> Clock**.
- When packets are sent, the device receives them without error, but defaults back to Clock display unless an active **Drawing Pad Session (`SPP_DRAWING_PAD_ENTER` / `SPP_DRAWING_ENCODE_PIC`)** or **Custom Gallery Channel** handshake is established.

---

## 3. Prioritized Next Steps

1. **Extract Exact Drawing Pad Protocol Sequence**:
   - Inspect `com.divoom.Divoom.bluetooth.SppProc` and `DesignSyncSendModel` in the attached APK (`com.divoom.Divoom_3.8.50-650_minAPI24...apk`) using `jadx` or APK decompiler to extract the exact byte packet emitted when the official Android app opens the drawing canvas and sends a 16x16 pixel frame.
2. **Channel Selection Handshake**:
   - Identify the exact unlock command that keeps the Timebox-Evo display in Custom Canvas Mode without reverting back to the clock.
3. **Paced BLE Frame Streaming in Daemon**:
   - Update `divoom_daemon.py` to use `BleakClient` continuously with the verified packet sequence so that changes in `state.json` animate in real time.

---

## 4. Key Repository Files

- [README.md](file:///Users/Opencode/FIRMWARE/DIVOO/README.md) - User guide and setup.
- [divoom_protocol.py](file:///Users/Opencode/FIRMWARE/DIVOO/divoom_protocol.py) - Checksum, byte escaping, and frame packet builders.
- [pixel_assets.py](file:///Users/Opencode/FIRMWARE/DIVOO/pixel_assets.py) - 16x16 handcrafted animated state frames.
- [divoom_daemon.py](file:///Users/Opencode/FIRMWARE/DIVOO/divoom_daemon.py) - State polling daemon.
- [ag_status_hook.py](file:///Users/Opencode/FIRMWARE/DIVOO/ag_status_hook.py) - CLI state modifier.
- [state.json](file:///Users/Opencode/FIRMWARE/DIVOO/state.json) - Active state file.
