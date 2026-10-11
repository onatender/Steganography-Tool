"""STEGTR01 codec, compatible with the original C# application.

Pixels are packed RGBA, row-major, with no row padding.
"""
import hashlib
import hmac
import struct
import os

from Cryptodome.Cipher import AES
from Cryptodome.Protocol.KDF import scrypt

MAGIC = b"STEGTR01"
HEADER_SIZE = 44
ENCRYPTED_MAGIC = b"STEGTR02"
ENCRYPTION_OVERHEAD = 16 + 12 + 16  # salt, nonce, GCM tag


def _key(password: str, salt: bytes) -> bytes:
    if not password:
        raise StegError("Enter the password used to protect this data.")
    return scrypt(password.encode("utf-8"), salt, key_len=32, N=2**15, r=8, p=1)


class StegError(ValueError):
    pass


def capacity(width: int, height: int, encrypted: bool = False) -> int:
    return max(0, width * height * 3 // 8 - HEADER_SIZE - (ENCRYPTION_OVERHEAD if encrypted else 0))


def pack(name: str, data: bytes) -> bytes:
    encoded = name.encode("utf-8")
    return struct.pack("<I", len(encoded)) + encoded + data


def unpack(payload: bytes) -> tuple[str, bytes]:
    if len(payload) < 4:
        raise StegError("The hidden data header is invalid.")
    length = struct.unpack_from("<I", payload)[0]
    if length > len(payload) - 4:
        raise StegError("The hidden file name is corrupted.")
    try:
        name = payload[4:4 + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StegError("The hidden file name could not be read.") from exc
    return name, payload[4 + length:]


def _validate_pixels(pixels: bytes, width: int, height: int) -> None:
    if width <= 0 or height <= 0 or len(pixels) != width * height * 4:
        raise StegError("The image pixel data is invalid.")


def embed(pixels: bytes, width: int, height: int, payload: bytes, password: str | None = None, progress=None) -> bytes:
    report = progress or (lambda percent, message: None)
    report(0, "Preparing content")
    _validate_pixels(pixels, width, height)
    if width * height * 3 < HEADER_SIZE * 8:
        raise StegError("This image is too small to hold hidden data.")
    if len(payload) > capacity(width, height, password is not None):
        raise StegError("There is not enough space in this image. Choose a larger image or reduce the content size.")
    magic = MAGIC
    if password is not None:
        report(5, "Encrypting content with AES")
        salt, nonce = os.urandom(16), os.urandom(12)
        cipher = AES.new(_key(password, salt), AES.MODE_GCM, nonce=nonce)
        cipher.update(ENCRYPTED_MAGIC)
        ciphertext, tag = cipher.encrypt_and_digest(payload)
        payload = salt + nonce + ciphertext + tag
        magic = ENCRYPTED_MAGIC
        if len(payload) > capacity(width, height):
            raise StegError("The encrypted data does not fit in this image.")
    packet = magic + struct.pack("<I", len(payload)) + hashlib.sha256(payload).digest() + payload
    result = bytearray(pixels)
    offset = 0
    interval = max(4096, len(packet) // 100)
    report(10, "Embedding content in the image")
    for index, value in enumerate(packet):
        for bit in range(8):
            result[offset] = (result[offset] & 0xFE) | ((value >> bit) & 1)
            offset += 1
            if offset % 4 == 3:
                offset += 1
        if index % interval == 0:
            report(10 + (index + 1) * 75 // len(packet), "Embedding content in the image")
    report(85, "Image data is ready")
    return bytes(result)


def _read(pixels: bytes, length: int, progress=None) -> bytes:
    result = bytearray(length)
    offset = 0
    interval = max(4096, length // 100)
    for i in range(length):
        value = 0
        for bit in range(8):
            value |= (pixels[offset] & 1) << bit
            offset += 1
            if offset % 4 == 3:
                offset += 1
        result[i] = value
        if progress is not None and i % interval == 0:
            progress(5 + (i + 1) * 80 // max(1, length), "Reading hidden content")
    return bytes(result)


def is_encrypted(pixels: bytes, width: int, height: int) -> bool:
    """Inspect the format so the interface only asks for a password when needed."""
    _validate_pixels(pixels, width, height)
    if width * height * 3 < HEADER_SIZE * 8:
        raise StegError("This image is too small to hold hidden data.")
    header = _read(pixels, HEADER_SIZE)
    if header[:8] not in (MAGIC, ENCRYPTED_MAGIC):
        raise StegError("No hidden data was found. Select the original PNG that contains the hidden data.")
    length = struct.unpack_from("<I", header, 8)[0]
    if length > capacity(width, height) or (header[:8] == ENCRYPTED_MAGIC and length < ENCRYPTION_OVERHEAD):
        raise StegError("The hidden data header is corrupted.")
    return header[:8] == ENCRYPTED_MAGIC


def extract(pixels: bytes, width: int, height: int, password: str | None = None, progress=None) -> bytes:
    report = progress or (lambda percent, message: None)
    report(0, "Checking image")
    _validate_pixels(pixels, width, height)
    if width * height * 3 < HEADER_SIZE * 8:
        raise StegError("This image is too small to hold hidden data.")
    header = _read(pixels, HEADER_SIZE)
    if header[:8] not in (MAGIC, ENCRYPTED_MAGIC):
        raise StegError("No hidden data was found. Select a PNG created by this app.")
    length = struct.unpack_from("<I", header, 8)[0]
    if length > capacity(width, height):
        raise StegError("The hidden data header is corrupted. Try the original PNG file.")
    payload = _read(pixels, HEADER_SIZE + length, progress=progress)[HEADER_SIZE:]
    report(85, "Verifying content integrity")
    if not hmac.compare_digest(hashlib.sha256(payload).digest(), header[12:44]):
        raise StegError("The hidden data is corrupted. The image may have been resized or compressed.")
    if header[:8] == ENCRYPTED_MAGIC:
        if len(payload) < ENCRYPTION_OVERHEAD:
            raise StegError("The encrypted data header is corrupted.")
        report(90, "Verifying password and decrypting")
        key = _key(password, payload[:16])
        try:
            cipher = AES.new(key, AES.MODE_GCM, nonce=payload[16:28])
            cipher.update(ENCRYPTED_MAGIC)
            decrypted = cipher.decrypt_and_verify(payload[28:-16], payload[-16:])
            report(100, "Content unlocked")
            return decrypted
        except ValueError as exc:
            raise StegError("The password is incorrect or the encrypted data is corrupted.") from exc
    report(100, "Content unlocked")
    return payload
