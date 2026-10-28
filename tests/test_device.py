"""Device protocol tests against an emulated T5L (no hardware needed)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

from opendgus.device import dwinload as dl


class FakeScreen:
    """Minimal DGUS II UART2 emulation: 0x82/0x83, 0x00AA mode 2 block write, 0x0006 8051 update."""

    def __init__(self, crc=False, noise=b""):
        self.vp = [0] * 0x10000
        self.vp[0x000F] = 0x0063
        self.flash = bytearray(b"\xFF" * 16 * 1024 * 1024)
        self.code = bytearray(64 * 1024)
        self.crc, self.out, self.inbuf = crc, bytearray(noise), bytearray()

    # serial-port interface
    def write(self, data):
        self.inbuf += data
        while len(self.inbuf) >= 3 and len(self.inbuf) >= 3 + self.inbuf[2]:
            n = self.inbuf[2]
            body = bytes(self.inbuf[3:3 + n])
            del self.inbuf[:3 + n]
            if self.crc:
                assert dl.crc16_modbus(body[:-2]).to_bytes(2, "little") == body[-2:], "bad CRC from host"
                body = body[:-2]
            self.handle(body)

    def read(self, n):
        r = bytes(self.out[:n])
        del self.out[:n]
        return r

    def reply(self, cmd, payload):
        self.out += dl.frame(cmd, payload, self.crc)

    def handle(self, body):
        cmd, vp, data = body[0], int.from_bytes(body[1:3], "big"), body[3:]
        if cmd == 0x82:
            if len(data) % 2:  # byte write = high byte only
                self.vp[vp] = (data[0] << 8) | (self.vp[vp] & 0xFF)
            for i in range(0, len(data) - 1, 2):
                self.vp[vp + i // 2] = int.from_bytes(data[i:i + 2], "big")
            self.reply(0x82, b"OK")
            self.run_system(vp)
        elif cmd == 0x83:
            n = data[0]
            self.reply(0x83, body[1:3] + bytes([n]) + dl.words_to_bytes(self.vp[vp:vp + n]))

    def ram_bytes(self, vp, nbytes):
        return dl.words_to_bytes(self.vp[vp:vp + nbytes // 2])

    def run_system(self, vp):
        if vp == 0x00AA and self.vp[0xAA] == 0x5A02:
            block, src = self.vp[0xAB], self.vp[0xAC]
            self.flash[block * dl.BLOCK_SIZE:(block + 1) * dl.BLOCK_SIZE] = self.ram_bytes(src, dl.BLOCK_SIZE)
            self.vp[0xAA] = 0x0002
        if vp == 0x00AA and self.vp[0xAA] == 0x5A01:
            slot, word = self.vp[0xAB] >> 8, ((self.vp[0xAB] & 0xFF) << 16) | self.vp[0xAC]
            dst, n = self.vp[0xAD], self.vp[0xAE]
            src = slot * dl.SLOT_SIZE + word * 2
            for i in range(n):
                self.vp[dst + i] = int.from_bytes(self.flash[src + 2 * i:src + 2 * i + 2], "big")
            self.vp[0xAA] = 0x0001
        if vp == 0x0006 and self.vp[0x06] == 0x5AA5:
            self.code[:] = self.ram_bytes(self.vp[0x07], dl.OS_CODE_SIZE)
            self.vp[0x06] = 0x00A5


class FrameTests(unittest.TestCase):
    def test_manual_examples(self):
        self.assertEqual(dl.frame(0x83, bytes.fromhex("000F01"), True).hex(" ").upper(), "5A A5 06 83 00 0F 01 ED 90")
        self.assertEqual(dl.frame(0x82, bytes.fromhex("00820A"), True).hex(" ").upper(), "5A A5 06 82 00 82 0A C8 FB")
        self.assertEqual(dl.frame(0x82, bytes.fromhex("00845A010001")).hex(" ").upper(), "5A A5 07 82 00 84 5A 01 00 01")

    def test_flash_command_frame(self):
        # manual example: 32.ICL first block = 0x0100, staged at VP 0x8000
        f = dl.frame(0x82, (0x00AA).to_bytes(2, "big") + dl.words_to_bytes([0x5A02, 0x0100, 0x8000, 100, 0, 0]))
        self.assertEqual(f[:12].hex(" ").upper(), "5A A5 0F 82 00 AA 5A 02 01 00 80 00")


class UploadTests(unittest.TestCase):
    def check_upload(self, crc, size, slot):
        # a stray touch auto-upload and a corrupted frame arrive before the first reply
        touch = dl.frame(0x83, bytes.fromhex("100101000A"), crc)
        scr = FakeScreen(crc=crc, noise=touch + (b"\x5A\xA5\x05\x82\x4F\x4B\x00\x00" if crc else b""))
        d = dl.Dgus(scr, crc=crc, timeout=1)
        data = os.urandom(size)
        d.upload_slot(data, slot, log=lambda *_: None)
        base = slot * dl.SLOT_SIZE
        self.assertEqual(bytes(scr.flash[base:base + size]), data)
        pad_end = base + -(-size // dl.BLOCK_SIZE) * dl.BLOCK_SIZE
        self.assertTrue(all(b == 0xFF for b in scr.flash[base + size:pad_end]))

    def test_upload_small_no_crc(self):
        self.check_upload(False, 4270, 32)

    def test_upload_multiblock_crc(self):
        self.check_upload(True, 3 * dl.BLOCK_SIZE + 123, 14)

    def test_upload_progress(self):
        d = dl.Dgus(FakeScreen(), timeout=1)
        seen = []
        d.upload_slot(os.urandom(dl.BLOCK_SIZE + 10), 32, log=lambda *_: None, progress=seen.append)
        self.assertEqual(seen, sorted(seen))
        self.assertEqual(seen[-1], 2 * dl.BLOCK_SIZE)
        self.assertIn(dl.BLOCK_SIZE, seen)                  # block 1 ends exactly at 32 KB

    def test_flash_read_roundtrip(self):
        scr = FakeScreen(crc=True)
        d = dl.Dgus(scr, crc=True)
        data = os.urandom(40000)
        d.upload_slot(data, 40, log=lambda *_: None)
        self.assertEqual(d.flash_read(40, 0, len(data)), data)
        self.assertEqual(d.flash_read(40, 20000, 100), data[20000:20100])
        with self.assertRaises(dl.DgusError):
            d.flash_read(13, 0, 16)

    def test_upload_8051(self):
        scr = FakeScreen()
        d = dl.Dgus(scr)
        code = os.urandom(2464)
        d.upload_8051(code, log=lambda *_: None)
        self.assertEqual(bytes(scr.code[:len(code)]), code)

    def test_read_write_helpers(self):
        scr = FakeScreen()
        d = dl.Dgus(scr)
        self.assertEqual(d.read_words(0x000F, 1), [0x0063])
        d.write_words(0x0084, [0x5A01, 3])
        self.assertEqual(scr.vp[0x84:0x86], [0x5A01, 3])
        d.write(0x0082, bytes([40]))
        self.assertEqual(scr.vp[0x82] >> 8, 40)

    def test_timeout(self):
        class Dead:
            def write(self, _): pass
            def read(self, _): return b""
        with self.assertRaises(dl.DgusError):
            dl.Dgus(Dead(), timeout=0.1).read_words(0x000F, 1)


class ScanTests(unittest.TestCase):
    def test_scan(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "13TouchFile.bin").write_bytes(b"\xFF\xFF")
            (t / "14ShowFile.bin").write_bytes(b"\0" * 100)
            (t / "32_bg.icl").write_bytes(b"\0" * (300 * 1024))      # slots 32-33
            (t / "33_icons.ICL").write_bytes(b"\0" * 10)              # overlaps 32
            (t / "T5LCFG.CFG").write_bytes(b"T5LC1")
            (t / "T5L51.bin").write_bytes(b"\0" * 10)
            (t / "readme.txt").write_text("x")
            files, errors, warnings = dl.scan(t)
            kinds = {f.path.name: (f.kind, f.slot) for f in files}
            self.assertEqual(kinds["13TouchFile.bin"], ("slot", 13))
            self.assertEqual(kinds["T5LCFG.CFG"], ("cfg", None))
            self.assertEqual(kinds["T5L51.bin"], ("os8051", None))
            self.assertEqual(kinds["readme.txt"], ("other", None))
            self.assertEqual(len(errors), 1)
            self.assertIn("overlaps", errors[0])
            _, errors8, _ = dl.scan(t, flash_mb=8)  # 8 MB = slots 0-31, so 32+ is out of range
            self.assertTrue(any("flash has 0-31" in e for e in errors8))


if __name__ == "__main__":
    unittest.main(verbosity=2)
