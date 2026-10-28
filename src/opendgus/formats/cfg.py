"""Decode a DWIN T5L hardware config file (T5LCFG*.CFG).
Layout from T5L_DGUSII-Application-Development-Guide-V2.921 sec 3.3.2.5 (PDF p.25-32 / txt lines 650-940)
and COF-Screen-Application-DevelopmentT5L_DGUSII20220610 sec 5.1. Usage: python -I t5lcfg.py FILE"""
import sys

ROT = {0: "0", 1: "90", 2: "180", 3: "270"}
TP_TYPES = {0x0: "4-wire RTP", 0x1: "CTP GT911/GT9271/GT9110", 0x2: "ILI9881H in-cell CTP",
            0x3: "CTP ILI2117-class", 0x4: "CTP ILI2130-class", 0x5: "CTP BL8825 (Betterlife)",
            0x6: "CTP GSL1680 (Silead)", 0x7: "CTP CST340 (Hynitron)", 0x8: "CTP ILI231x/251x",
            0xF: "5-wire RTP"}

def u16(b, o): return (b[o] << 8) | b[o + 1]

def decode(b: bytes):
    out = []
    def g(o, n=1):
        return None if o + n > len(b) else (b[o] if n == 1 else u16(b, o))
    def add(o, n, name, val, meaning=""):
        raw = "n/a (beyond EOF)" if val is None else (f"0x{val:0{2*n}X}")
        out.append(f"0x{o:02X} [{n}] {name:24s} {raw:18s} {meaning if val is not None else 'not present -> device keeps current value (unverified)'}")
    magic = b[:5]
    out.append(f"0x00 [5] magic                    {magic.hex(' ').upper()}  {'OK (\"T5LC1\")' if magic == b'T5LC1' else 'BAD, expected 54 35 4C 43 31'}")
    v = g(5)
    if v is not None:
        add(5, 1, "SYS_CFG", v, f"CRC={'on' if v&0x80 else 'off'} audio={'music(WAE)' if v&0x40 else 'buzzer'} "
            f"load22={'yes' if v&0x20 else 'no'} touchAutoUpload={'on' if v&0x10 else 'off'} "
            f"touchBeep={'on' if v&8 else 'off'} blStandby={'on' if v&4 else 'off'} rotation={ROT[v&3]}deg")
    v = g(6)
    if v is not None:
        add(6, 1, "SYS_CFG1", v, f"PWMbacklight={'1kHz PWM' if v&0x80 else 'user'} NAND={'yes' if v&0x40 else 'no'} "
            f"NANDformat={'YES' if v&0x20 else 'no'} NAND={'4Gb' if v&0x10 else '1Gb'} eraseIntFlash={'YES' if v&8 else 'no'} "
            f"AD={'16bit' if v&4 else '12bit'} 8051enc={'yes' if v&2 else 'no'} OScoreDuringSD={'run' if v&1 else 'stop'}")
    v = g(7);  add(7, 1, "WAE_ID", v, f"music file id {v}" if v is not None else "")
    v = g(8);  add(8, 1, "BG_ICL_ID", v, f"background ICL = {v}.ICL" if v is not None else "")
    v = g(9);  add(9, 1, "TP_RATE_DIV", v, f"touch report rate {400/v:.1f} Hz (400Hz/val)" if v else "")
    v = g(0x0A, 2); add(0x0A, 2, "UART2_BAUD_DIV", v, f"{3225600/v:.0f} bps (3225600/val)" if v else "")
    v = g(0x0C); add(0x0C, 1, "BL_ON", v, f"{v}% normal/startup brightness" if v is not None else "")
    v = g(0x0D); add(0x0D, 1, "BL_STANDBY", v, f"{v}% standby brightness" if v is not None else "")
    v = g(0x0E, 2); add(0x0E, 2, "BL_STANDBY_TIME", v, f"{(v or 0)*10/1000:.2f} s before dimming" if v is not None else "")
    v = g(0x10, 2); en = v == 0x5AA5
    add(0x10, 2, "LCD_CFG_EN", v, "LCD timing 0x12-0x1F APPLIED" if en else "LCD timing below IGNORED (not 0x5AA5)")
    v = g(0x12); add(0x12, 1, "PCLK_PHS", v, "")
    v = g(0x13); add(0x13, 1, "PCLK_DIV", v, f"PCLK = {206.4384/v:.2f} MHz" if v else "")
    for o, n, nm in [(0x14,1,"H_W (hsync width)"),(0x15,1,"H_S (h back porch?)"),(0x16,2,"H_D (h res)"),(0x18,1,"H_E (h front porch?)"),
                     (0x19,1,"V_W (vsync width)"),(0x1A,1,"V_S (v back porch?)"),(0x1B,2,"V_D (v res)"),(0x1D,1,"V_E (v front porch?)"),
                     (0x1E,1,"TCON_SEL"),(0x1F,1,"reserved")]:
        v = g(o, n); add(o, n, nm, v, f"= {v}" if v is not None else "")
    v = g(0x20); add(0x20, 1, "TP_SET_EN", v, "TP config APPLIED" if v == 0x5A else "TP config 0x21-0x23 IGNORED")
    v = g(0x21)
    if v is not None:
        add(0x21, 1, "TP_MODE", v, f"type={TP_TYPES.get(v>>4,'?')} RTPcal={'on' if v&8 else 'off'} "
            f"Xinv={v>>2&1} Yinv={v>>1&1} XYswap={v&1}")
    v = g(0x22); add(0x22, 1, "TP_SENSE", v, "")
    v = g(0x23); add(0x23, 1, "TP_FREQ", v, "")
    v = g(0x24); add(0x24, 1, "CKO_SET_EN", v, "")
    v = g(0x25); add(0x25, 1, "CKO_EN", v, "")
    v = g(0x26); add(0x26, 1, "CKO_DIV", v, "")
    v = g(0x27); add(0x27, 1, "BUZZ_SET_EN", v, "")
    v = g(0x28); add(0x28, 1, "BUZZ_DIV1", v, "")
    v = g(0x29, 2); add(0x29, 2, "BUZZ_DIV2", v, "")
    v = g(0x2B, 2); add(0x2B, 2, "BUZZ_DUTY", v, "")
    v = g(0x2D); add(0x2D, 1, "BUZZ_TIME", v, f"{(v or 0)*10} ms" if v is not None else "")
    v = g(0x2E); add(0x2E, 1, "INIT_FILE_EN", v, "")
    v = g(0x2F); add(0x2F, 1, "INIT_FILE_ID", v, "")
    v = g(0x30); add(0x30, 1, "SYSCLK_SET_EN", v, "")
    v = g(0x31); add(0x31, 1, "SYSCLK_ADJ", v, "")
    v = g(0x32); add(0x32, 1, "PIC_REPLACE_EN", v, "")
    v = g(0x33); add(0x33, 1, "PIC_REPLACE_ICL", v, "")
    v = g(0x40, 2); add(0x40, 2, "SD_DIR_SET_EN", v, "")
    if len(b) >= 0x4B:
        out.append(f"0x42..0x4A SD folder name: len={b[0x42]} name={b[0x43:0x43+b[0x42]]!r}")
    v = g(0x70); add(0x70, 1, "BL_DELAY_EN", v, "")
    v = g(0x71); add(0x71, 1, "BL_DELAY", v, f"{(v or 0)*10} ms" if v is not None else "")
    out.append(f"file length = {len(b)} bytes (0x{len(b):X})")
    return "\n".join(out)

if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    print(data.hex(" ").upper())
    print(decode(data))
