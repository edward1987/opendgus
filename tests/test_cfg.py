from opendgus.formats.cfg import CfgOptions, build_cfg, decode, sys_cfg_byte

# DWIN's sample T5LCFG.CFG (DGUS V7.651 Config/), first 0x10 bytes = the common options
DWIN_SAMPLE_HEAD = bytes.fromhex("54354C4331380000202800 1C40000000".replace(" ", ""))


def test_defaults_match_dwin_sample_options():
    b = build_cfg()
    assert len(b) == 0x24
    assert b[:0x10] == DWIN_SAMPLE_HEAD
    assert b[0x10:0x12] == b"\0\0"          # LCD timing disabled
    assert b[0x20] == 0                      # touch controller config disabled


def test_never_sets_dangerous_bits():
    b = build_cfg(CfgOptions(rotation=270, uart_crc=True, baud=460800, background_icl=23))
    assert b[6] == 0                         # no NAND format / flash erase / encryption
    assert b[5] & 3 == 3 and b[5] & 0x80
    assert int.from_bytes(b[10:12], "big") == 7
    assert b[8] == 23


def test_unreachable_baud_rejected():
    import pytest
    with pytest.raises(ValueError):
        build_cfg(CfgOptions(baud=921600))       # 3225600/921600 = 3.5, not an integer divider


def test_sys_cfg_matches_hardware_readback():
    # 0x0080 read from the user's display: low byte 0x38 = load 22, auto-upload, beep, 0 deg
    assert sys_cfg_byte(CfgOptions()) == 0x38


def test_decode_reads_back():
    text = decode(build_cfg(CfgOptions(backlight=100, baud=9600)))
    assert "9600 bps" in text and "100%" in text
