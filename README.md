# Divoom Timebox-Evo Antigravity Status Display

Turn your **Divoom Timebox-Evo** (16x16 RGB LED display) into a physical live status monitor for **Google Antigravity**.

---

## Features

- **Direct macOS Bluetooth Classic (RFCOMM/SPP)** connection using native `IOBluetooth` (PyObjC).
- **Zero Cloud / Zero Vendor Lock-in**: Directly drives the device with custom 16x16 pixel art animations.
- **Dynamic State Synchronization**:
  - `IDLE`: Soft glowing Antigravity icon
  - `THINKING` / `PLANNING`: Rotating cyan/purple neural sparkle
  - `RUNNING_TOOL`: Terminal screen with blinking cursor
  - `WAITING_USER`: Pulsing amber attention badge
  - `SUCCESS`: Green checkmark flourish
  - `ERROR`: Red alert octagon
- **Antigravity Hook Integration**: Updates dynamically via `~/.antigravity/state.json`.

---

## 1. Prerequisites & Bluetooth Pairing

1. Put your **Divoom Timebox-Evo** into Bluetooth pairing mode.
2. Open **macOS System Settings > Bluetooth** and pair with `Timebox-Evo` (or `Timebox-Evo-audio`).
3. Confirm the device appears in your paired devices list.

---

## 2. Setup

Inside this directory (`/Users/Opencode/FIRMWARE/DIVOO`):

```bash
# Activate the pre-configured virtual environment
source .venv/bin/activate

# Scan and verify that your Timebox-Evo is detected by macOS IOBluetooth:
python mac_bluetooth.py
```

---

## 3. Testing States & Animations

To test all 6 animation states on your Timebox-Evo:

```bash
# Live on device:
python divoom_daemon.py --test-states

# Or test in dry-run/preview mode:
python divoom_daemon.py --dry-run --test-states
```

---

## 4. Running the Live Daemon

Start the daemon to monitor Antigravity in real-time:

```bash
python divoom_daemon.py
```

To emit state changes manually or from a hook:

```bash
# Indicate thinking
python ag_status_hook.py --state thinking

# Indicate tool execution
python ag_status_hook.py --state running_tool --tool run_command

# Indicate waiting for user input
python ag_status_hook.py --state waiting_user

# Indicate task completion
python ag_status_hook.py --state success
```
