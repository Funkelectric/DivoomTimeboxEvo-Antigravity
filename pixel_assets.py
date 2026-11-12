"""
Pixel art definitions and animation frames for Antigravity states (16x16 RGB).
"""

from typing import List, Tuple

RGB = Tuple[int, int, int]
Frame = List[RGB]

# Color Palette
BLACK: RGB = (0, 0, 0)
WHITE: RGB = (255, 255, 255)
CYAN: RGB = (0, 220, 255)
BLUE: RGB = (30, 100, 255)
PURPLE: RGB = (160, 32, 240)
GREEN: RGB = (0, 230, 70)
DARK_GREEN: RGB = (0, 100, 30)
AMBER: RGB = (255, 170, 0)
ORANGE: RGB = (255, 110, 0)
RED: RGB = (255, 40, 40)
DARK_RED: RGB = (120, 10, 10)
GRAY: RGB = (80, 80, 80)
DARK_GRAY: RGB = (35, 35, 35)

def create_blank_frame(color: RGB = BLACK) -> Frame:
    return [color] * 256

def set_pixel(frame: Frame, x: int, y: int, color: RGB):
    if 0 <= x < 16 and 0 <= y < 16:
        frame[y * 16 + x] = color

# --- 1. IDLE (Antigravity 'A' Logo with breathing ambient glow) ---
def get_idle_frames() -> List[Frame]:
    frames = []
    # 4 breathing glow levels
    shades = [
        ((0, 60, 90), (0, 140, 180)),
        ((0, 90, 140), (0, 180, 230)),
        ((0, 130, 200), (0, 220, 255)),
        ((0, 90, 140), (0, 180, 230)),
    ]
    for bg_c, fg_c in shades:
        f = create_blank_frame(BLACK)
        # Draw stylized triangular chevron / AG monogram
        coords = [
            (7, 3), (8, 3),
            (6, 4), (9, 4),
            (5, 5), (10, 5),
            (5, 6), (10, 6),
            (4, 7), (5, 7), (6, 7), (7, 7), (8, 7), (9, 7), (10, 7), (11, 7),
            (4, 8), (11, 8),
            (3, 9), (12, 9),
            (3, 10), (12, 10),
            (2, 11), (13, 11),
            (2, 12), (13, 12)
        ]
        for x, y in coords:
            set_pixel(f, x, y, fg_c)
        # Center core dot
        set_pixel(f, 7, 5, bg_c)
        set_pixel(f, 8, 5, bg_c)
        frames.append(f)
    return frames

# --- 2. THINKING / PLANNING (Rotating Cyan/Purple Neural Sparkle) ---
def get_thinking_frames() -> List[Frame]:
    frames = []
    # 4 rotation angles
    patterns = [
        # Frame 0: Cross +
        [(7, 4), (8, 4), (7, 11), (8, 11), (4, 7), (4, 8), (11, 7), (11, 8)],
        # Frame 1: Diagonal X
        [(5, 5), (6, 5), (10, 5), (9, 5), (5, 10), (6, 10), (10, 10), (9, 10)],
        # Frame 2: Outer Box
        [(6, 4), (9, 4), (4, 6), (11, 6), (4, 9), (11, 9), (6, 11), (9, 11)],
        # Frame 3: Secondary diagonal
        [(5, 6), (6, 5), (9, 6), (10, 5), (5, 9), (6, 10), (9, 9), (10, 10)],
    ]
    for p in patterns:
        f = create_blank_frame(BLACK)
        # Central pulsing nucleus
        for cx in (7, 8):
            for cy in (7, 8):
                set_pixel(f, cx, cy, PURPLE)
        # Outer orbiting nodes
        for px, py in p:
            set_pixel(f, px, py, CYAN)
        frames.append(f)
    return frames

# --- 3. RUNNING TOOL (Terminal Prompt '>_' with Blinking Cursor) ---
def get_tool_frames() -> List[Frame]:
    frames = []
    prompt = [
        (3, 5),
        (4, 6),
        (5, 7),
        (4, 8),
        (3, 9),
    ]
    for blink in (True, False):
        f = create_blank_frame(BLACK)
        # Blue border outline
        for i in range(1, 15):
            set_pixel(f, i, 2, BLUE)
            set_pixel(f, i, 13, BLUE)
            set_pixel(f, 1, i, BLUE)
            set_pixel(f, 14, i, BLUE)
        # Green prompt symbol >
        for px, py in prompt:
            set_pixel(f, px, py, GREEN)
        # Blinking cursor _
        if blink:
            for cx in range(7, 12):
                set_pixel(f, cx, 9, WHITE)
                set_pixel(f, cx, 10, WHITE)
        frames.append(f)
    return frames

# --- 4. WAITING FOR USER (Amber Question Mark Pulsing) ---
def get_waiting_frames() -> List[Frame]:
    frames = []
    q_pixels = [
        (6, 4), (7, 3), (8, 3), (9, 4),
        (9, 5), (8, 6), (7, 7),
        (7, 8),
        (7, 10), (7, 11)  # Dot
    ]
    for col in (AMBER, ORANGE):
        f = create_blank_frame(BLACK)
        # Outer soft border
        for x in (5, 10):
            for y in range(3, 13):
                set_pixel(f, x, y, DARK_GRAY)
        for px, py in q_pixels:
            set_pixel(f, px, py, col)
            set_pixel(f, px + 1, py, col)
        frames.append(f)
    return frames

# --- 5. SUCCESS (Green Checkmark Flourish) ---
def get_success_frames() -> List[Frame]:
    frames = []
    check_coords = [
        (3, 8), (4, 9), (5, 10), (6, 11),
        (7, 10), (8, 9), (9, 8), (10, 7), (11, 6), (12, 5)
    ]
    for border_glow in (DARK_GREEN, GREEN):
        f = create_blank_frame(BLACK)
        # Circle badge outline
        for i in range(3, 13):
            set_pixel(f, i, 1, border_glow)
            set_pixel(f, i, 14, border_glow)
            set_pixel(f, 1, i, border_glow)
            set_pixel(f, 14, i, border_glow)
        # Checkmark
        for x, y in check_coords:
            set_pixel(f, x, y, WHITE)
            set_pixel(f, x, y + 1, GREEN)
        frames.append(f)
    return frames

# --- 6. ERROR / ALERT (Red Warning Octagon / Exclamation) ---
def get_error_frames() -> List[Frame]:
    frames = []
    exclamation = [
        (7, 4), (8, 4),
        (7, 5), (8, 5),
        (7, 6), (8, 6),
        (7, 7), (8, 7),
        (7, 8), (8, 8),
        (7, 11), (8, 11),  # Dot
    ]
    for flash_c in (RED, DARK_RED):
        f = create_blank_frame(flash_c)
        for x in range(3, 13):
            for y in range(3, 13):
                set_pixel(f, x, y, BLACK)
        for x, y in exclamation:
            set_pixel(f, x, y, RED)
        frames.append(f)
    return frames

STATE_MAP = {
    "idle": get_idle_frames,
    "thinking": get_thinking_frames,
    "planning": get_thinking_frames,
    "running_tool": get_tool_frames,
    "waiting_user": get_waiting_frames,
    "success": get_success_frames,
    "error": get_error_frames,
}

def get_frames_for_state(state_name: str) -> List[Frame]:
    builder = STATE_MAP.get(state_name.lower(), get_idle_frames)
    return builder()
