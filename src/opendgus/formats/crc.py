"""CRC-16/MODBUS as used by DWIN files and UART frames."""
import struct

# ---------------------------------------------------------------------------
# CRC: Modbus CRC-16 (poly 0xA001 reflected, init 0xFFFF). DWIN's table code keeps the
# result in (CRCH, CRCL) where CRCH == std_crc & 0xFF; files store CRCH then CRCL, i.e. the
# standard CRC-16/MODBUS value little-endian.
# ---------------------------------------------------------------------------

def crc16_modbus(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def dwin_crc_bytes(data: bytes) -> bytes:
    """Two bytes exactly as DWIN writes them at ICL offset 6..7."""
    return struct.pack('<H', crc16_modbus(data))


