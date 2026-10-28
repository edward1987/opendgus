"""DGUS II UART2 frame helpers + CRC16 check against manual examples.
CRC: CRC-16/MODBUS (poly 0x8005 reflected = 0xA001, init 0xFFFF), appended LOW byte first,
computed over cmd byte .. end of data (not over 5A A5 or LEN)."""
import sys

def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc

def frame(cmd: int, payload: bytes, crc: bool = False) -> bytes:
    body = bytes([cmd]) + payload
    if crc:
        c = crc16_modbus(body)
        body += bytes([c & 0xFF, c >> 8])
    return b"\x5A\xA5" + bytes([len(body)]) + body

def write_vp(vp: int, words, crc=False) -> bytes:
    p = vp.to_bytes(2, "big") + b"".join(w.to_bytes(2, "big") for w in words)
    return frame(0x82, p, crc)

def read_vp(vp: int, nwords: int, crc=False) -> bytes:
    return frame(0x83, vp.to_bytes(2, "big") + bytes([nwords]), crc)

def h(b): return " ".join(f"{x:02X}" for x in b)

if __name__ == "__main__":
    # Examples from T5L_DGUSII-Application-Development-Guide-V2.921 p.33-34 / p.44
    checks = [
        ("read ver 0x000F crc", read_vp(0x000F, 1, True), "5A A5 06 83 00 0F 01 ED 90"),
        ("backlight 0x82=0x0A crc (byte write)", frame(0x82, bytes.fromhex("00820A"), True), "5A A5 06 82 00 82 0A C8 FB"),
        ("write 0x1000=3132 crc", write_vp(0x1000, [0x3132], True), "5A A5 07 82 10 00 31 32 CC 9B"),
        ("OK reply crc", frame(0x82, b"\x4F\x4B", True), "5A A5 05 82 4F 4B A5 EF"),
        ("read reply crc", frame(0x83, bytes.fromhex("000F011410"), True), "5A A5 08 83 00 0F 01 14 10 43 F0"),
        ("touch upload crc", frame(0x83, bytes.fromhex("100101005A"), True), "5A A5 08 83 10 01 01 00 5A 0E 2C"),
        ("UART cfg CRC off", frame(0x82, bytes.fromhex("000C5A00"), True), "5A A5 07 82 00 0C 5A 00 A6 BD"),
        ("UART cfg 115200 no CRC (sent w/ CRC)", frame(0x82, bytes.fromhex("000C5A00001C"), True), "5A A5 09 82 00 0C 5A 00 00 1C BA 18"),
        ("ver reply V63/22 crc", frame(0x83, bytes.fromhex("000F016322"), True), "5A A5 08 83 00 0F 01 63 22 E5 D5"),
        ("reset", write_vp(0x0004, [0x55AA, 0x5AA5]), "5A A5 07 82 00 04 55 AA 5A A5"),
        ("page switch to 1", write_vp(0x0084, [0x5A01, 0x0001]), "5A A5 07 82 00 84 5A 01 00 01"),
    ]
    ok = True
    for name, got, exp in checks:
        r = h(got) == exp
        ok &= r
        print(f"{'OK ' if r else 'BAD'} {name:40s} {h(got)}" + ("" if r else f"   expected {exp}"))
    sys.exit(0 if ok else 1)
