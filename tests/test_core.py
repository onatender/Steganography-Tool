import struct
import hashlib
import unittest
from steg_core import StegError, capacity, embed, extract, pack, unpack, _read, HEADER_SIZE, ENCRYPTED_MAGIC


class CodecTests(unittest.TestCase):
    def setUp(self):
        self.width, self.height = 80, 80
        self.pixels = bytes([90, 130, 190, 123]) * (self.width * self.height)

    def test_unicode_and_binary_round_trip(self):
        for name, data in [("", "Şığöüç Merhaba 🌿\nİkinci satır".encode()), ("örnek.bin", bytes(range(256))), ("boş.txt", b"")]:
            with self.subTest(name=name):
                encoded = embed(self.pixels, self.width, self.height, pack(name, data))
                self.assertEqual(unpack(extract(encoded, self.width, self.height)), (name, data))
                self.assertEqual(encoded[3::4], self.pixels[3::4])
                self.assertTrue(all(abs(a - b) <= 1 for a, b in zip(encoded, self.pixels)))

    def test_full_capacity_and_overflow(self):
        limit = capacity(self.width, self.height); payload = bytes(i % 256 for i in range(limit))
        encoded = embed(self.pixels, self.width, self.height, payload)
        self.assertEqual(extract(encoded, self.width, self.height), payload)
        with self.assertRaises(StegError): embed(self.pixels, self.width, self.height, payload + b"x")

    def test_corrupted_payload(self):
        encoded = bytearray(embed(self.pixels, self.width, self.height, pack("", b"hello")))
        bit = 44 * 8; encoded[(bit // 3) * 4 + bit % 3] ^= 1
        with self.assertRaisesRegex(StegError, "corrupted"): extract(encoded, self.width, self.height)

    def test_absent_invalid_and_small_images(self):
        with self.assertRaises(StegError): extract(self.pixels, self.width, self.height)
        with self.assertRaises(StegError): extract(b"\0" * 4, 1, 1)
        with self.assertRaises(StegError): embed(b"\0" * 4, 1, 1, b"")
        with self.assertRaises(StegError): embed(b"", self.width, self.height, b"")

    def test_corrupted_length(self):
        encoded = bytearray(embed(self.pixels, self.width, self.height, pack("", b"x")))
        for bit in range(8 * 8, 12 * 8): encoded[(bit // 3) * 4 + bit % 3] |= 1
        with self.assertRaisesRegex(StegError, "header is corrupted"): extract(encoded, self.width, self.height)

    def test_malformed_names(self):
        for data in [b"", struct.pack("<I", 100), struct.pack("<I", 1) + b"\xff"]:
            with self.assertRaises(StegError): unpack(data)

    def test_encrypted_roundtrip_and_passwords(self):
        for name, data in [("", "Şifreli mesaj 🌿".encode()), ("örnek.bin", bytes(range(256))), ("boş.txt", b"")]:
            payload = pack(name, data)
            encoded = embed(self.pixels, self.width, self.height, payload, password="Parola-ş🔑")
            self.assertEqual(unpack(extract(encoded, self.width, self.height, "Parola-ş🔑")), (name, data))
            self.assertEqual(encoded[3::4], self.pixels[3::4])
            self.assertNotIn(payload, _read(encoded, HEADER_SIZE + len(payload) + 44))
            for password in (None, "", "yanlış"):
                with self.assertRaises(StegError): extract(encoded, self.width, self.height, password)
            with self.assertRaises(StegError): embed(self.pixels, self.width, self.height, payload, "")

    def test_encrypted_capacity_randomness_and_legacy(self):
        limit = capacity(self.width, self.height, True)
        payload = b"x" * limit
        first = embed(self.pixels, self.width, self.height, payload, "secret")
        second = embed(self.pixels, self.width, self.height, payload, "secret")
        self.assertNotEqual(first, second)
        self.assertEqual(extract(first, self.width, self.height, "secret"), payload)
        with self.assertRaises(StegError): embed(self.pixels, self.width, self.height, payload + b"x", "secret")
        old = embed(self.pixels, self.width, self.height, b"legacy")
        self.assertEqual(extract(old, self.width, self.height, "unused"), b"legacy")

    def test_authenticated_tampering_even_with_recomputed_hash(self):
        encoded = embed(self.pixels, self.width, self.height, pack("secret.txt", b"secret"), "password")
        length = struct.unpack_from("<I", _read(encoded, HEADER_SIZE), 8)[0]
        payload = bytearray(_read(encoded, HEADER_SIZE + length)[HEADER_SIZE:])
        for index in (0, 16, 28, len(payload) - 1):
            tampered = payload.copy(); tampered[index] ^= 1
            packet = ENCRYPTED_MAGIC + struct.pack("<I", length) + hashlib.sha256(tampered).digest() + tampered
            pixels = bytearray(self.pixels)
            for pos in range(len(packet) * 8):
                offset = (pos // 3) * 4 + pos % 3
                pixels[offset] = (pixels[offset] & 254) | ((packet[pos // 8] >> (pos % 8)) & 1)
            with self.assertRaisesRegex(StegError, "password is incorrect"):
                extract(bytes(pixels), self.width, self.height, "password")

    def test_progress_reports_real_work_without_changing_output(self):
        pixels = bytes([90, 130, 190, 123]) * (640 * 480)
        payload = b"x" * 80000; events = []
        encoded = embed(pixels, 640, 480, payload, progress=lambda n, text: events.append((n, text)))
        self.assertEqual(encoded, embed(pixels, 640, 480, payload))
        values = [n for n, _ in events]
        self.assertEqual(values, sorted(values)); self.assertEqual(values[0], 0); self.assertEqual(values[-1], 85)
        self.assertGreater(len(set(values)), 10)
        events.clear(); self.assertEqual(extract(encoded, 640, 480, progress=lambda n, text: events.append((n, text))), payload)
        values = [n for n, _ in events]
        self.assertEqual(values, sorted(values)); self.assertEqual(values[-1], 100)


if __name__ == "__main__": unittest.main()
