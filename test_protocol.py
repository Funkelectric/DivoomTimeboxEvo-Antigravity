import unittest
from divoom_protocol import (
    calculate_checksum,
    escape_bytes,
    build_packet,
    encode_brightness,
    encode_16x16_frame,
    START_BYTE,
    END_BYTE,
    CMD_SET_BRIGHTNESS,
    CMD_SEND_STATIC_IMAGE
)

class TestDivoomProtocol(unittest.TestCase):
    def test_checksum(self):
        payload = bytes([0x74, 0x32])  # CMD_SET_BRIGHTNESS, 50%
        # 0x74 + 0x32 = 0xA6
        self.assertEqual(calculate_checksum(payload), 0x00A6)

    def test_escape(self):
        raw = bytes([0x00, 0x01, 0x02, 0x03, 0xFF])
        escaped = escape_bytes(raw)
        expected = bytes([0x00, 0x03, 0x04, 0x03, 0x05, 0x03, 0x06, 0xFF])
        self.assertEqual(escaped, expected)

    def test_build_packet(self):
        payload = bytes([0x74, 0x32])
        # length = 2 (payload) + 2 (checksum) = 4 -> [0x04, 0x00]
        # checksum = 0x00A6 -> [0xA6, 0x00]
        packet = build_packet(payload)
        self.assertEqual(packet[0], START_BYTE)
        self.assertEqual(packet[-1], END_BYTE)
        # Inner body should contain length, payload, checksum
        self.assertIn(bytes([0x74, 0x32]), packet)

    def test_encode_16x16_frame(self):
        # 256 black pixels
        pixels = [(0, 0, 0)] * 256
        packet = encode_16x16_frame(pixels)
        self.assertEqual(packet[0], START_BYTE)
        self.assertEqual(packet[-1], END_BYTE)

    def test_invalid_pixel_count(self):
        with self.assertRaises(ValueError):
            encode_16x16_frame([(0, 0, 0)] * 100)

if __name__ == "__main__":
    unittest.main()
