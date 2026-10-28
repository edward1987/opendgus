"""Text / data family specs (14.bin 0x12-0x18) must reproduce the C# vectors (tests/vectors/text.txt) and decode back."""
from pathlib import Path

import pytest

import opendgus.formats.specs  # noqa: F401  (fills the registry)
from opendgus.formats import spec

VEC = dict(line.split() for line in (Path(__file__).parent / "vectors" / "text.txt").read_text().splitlines()
           if line.strip())

# Same inputs as tools/csharp_harness/families/text.cs, expressed as spec fields
CASES = {
    "rtc_text": ("rtc_text", dict(sp=0x9300, x=400, y=20, color=0xFFE0, lib_id=3, spacing_flag=True, font_x=12,
                                  fmt="Y-M-D H:Q:S")),
    "rtc_text_long": ("rtc_text", dict(x=0, y=0, color=0x001F, lib_id=0, font_x=8, fmt="20Y-M-D W H:Q:S xyz")),
    "analog_clock": ("analog_clock", dict(x=400, y=240, icon_hour=1, hour_cx=5, hour_cy=60, icon_minute=2,
                                          minute_cx=4, minute_cy=90, icon_second=3, second_cx=2, second_cy=110,
                                          icon_lib=42)),
    "hex_data": ("hex_data", dict(sp=0x9400, vp=0x5060, x=50, y=60, color=0xF81F, byte_num=6, bcd=True, lib_id=0,
                                  font_x=16, string_code="2D2D203A3A")),
    "hex_data_bad_long": ("hex_data", dict(vp=0x5062, x=1, y=2, color=0, byte_num=0x13, bcd=False, lib_id=1,
                                           font_x=8, string_code="3AZZ2E0102030405060708090A0B0C0D0E0F")),
    "scroll_text": ("scroll_text", dict(sp=0x9500, vp=0x5100, rolling_mode=2, rolling_dis=3, adjust_mode=2,
                                        run_control=4, color=0x07FF, x1=10, y1=400, x2=900, y2=500, font0=0, font1=1,
                                        font_x=12, font_y=24, encode_mode=5, hor_dis=2, speed=7)),
    "data_window": ("data_window", dict(sp=0x9600, vp=0x5200, v_min=-20, v_max=120, n_int=3, n_dot=1, n_digit=5,
                                        zero_flag=True, plus_flag=True, wrap=False, spacing_flag=True, x=300, y=200,
                                        step=5, font0_x=16, font0_y=40, font0_color=0xF800, font1_x=12, font1_y=10,
                                        font1_color=0x8410, lib_id=24)),
    "data_window_font_clamp": ("data_window", dict(vp=0x5202, v_min=0, v_max=9, n_int=1, n_dot=0, n_digit=0,
                                                   wrap=True, x=10, y=20, step=1, font0_x=200, font0_y=100,
                                                   font0_color=0xFFFF, font1_x=8, font1_y=16, font1_color=0x1234,
                                                   lib_id=0)),
    "dgus2_text": ("dgus2_text", dict(sp=0x9700, vp=0x5300, x=20, y=30, color=0x7BEF, x1=20, y1=30, x2=820, y2=90,
                                      text_len=64, font_id=0x0102, spacing_flag=True, font_height=32, hor_dis=1,
                                      ver_dis=4, align=2)),
    "dgus2_text_big": ("dgus2_text", dict(vp=0x5310, x=0, y=0, color=0, x1=0, y1=0, x2=100, y2=500, text_len=8,
                                          font_id=5, font_height=1000, align=1)),
    "roll_character": ("roll_character", dict(sp=0x9800, vp=0x5400, data_type=0, lines=5, n_int=2, n_dot=1,
                                              data_gap=3, v_min=-10, v_max=50, zero_flag=True, plus_flag=True,
                                              align=0, speed=20, change_speed=2, font_id=7, font_set0=5,
                                              x=150, y=200, line_gap0=4, line_gap1=5, line_gap2=6, line_gap3=7,
                                              dim=0x80, line_height=40, font1=1, font2=2, font3=3, font4=4)),
    "roll_character_text": ("roll_character", dict(vp=0x5410, data_type=15, lines=3, char_len=10, text_vp=0x6000,
                                                   n_int=9, n_dot=9, data_gap=99, v_min=0, v_max=4, show_bk=True,
                                                   align=2, speed=63, change_speed=1, font_id=0x0203, font_set0=2,
                                                   x=110, y=50, dim=50, line_height=24, font1=15, font4=9)),
    "roll_character_left": ("roll_character", dict(vp=0x5420, data_type=1, lines=1, n_int=3, n_dot=0, data_gap=0,
                                                   v_min=0, v_max=-1, align=1, x=50, y=60, line_height=0)),
    "gtf_text": ("gtf_text", dict(sp=0x9900, vp=0x5500, gtf_id=0x40, font_id=12, x1=30, y1=40, x2=330, y2=140,
                                  hor_dis=2, ver_dis=3, opaque=True, no_reload=True, superimpose=False, align=2)),
    "gtf_text_left": ("gtf_text", dict(vp=0x5502, gtf_id=1, font_id=13, x1=5, y1=6, x2=70, y2=80, superimpose=True,
                                       align=0)),
}


def test_every_vector_has_a_case():
    assert set(VEC) == set(CASES)


@pytest.mark.parametrize("vec", sorted(CASES))
def test_spec_matches_csharp(vec):
    key, vals = CASES[vec]
    assert spec.encode(key, **vals).hex().upper() == VEC[vec]


@pytest.mark.parametrize("vec", sorted(CASES))
def test_decode_roundtrip(vec):
    raw = bytes.fromhex(VEC[vec])
    key, vals = spec.decode(raw)
    assert key == CASES[vec][0]
    assert spec.encode(key, **vals) == raw


def test_decoded_values_are_editor_values():
    _, v = spec.decode(bytes.fromhex(VEC["hex_data"]))
    assert v["string_code"] == "2D2D203A3A" and v["byte_num"] == 6 and v["bcd"] is True
    _, v = spec.decode(bytes.fromhex(VEC["roll_character_text"]))
    assert (v["lines"], v["char_len"], v["text_vp"], v["n_int"]) == (3, 10, 0x6000, 0)
    _, v = spec.decode(bytes.fromhex(VEC["data_window_font_clamp"]))
    assert (v["font0_x"], v["font0_y"]) == (200, 144)          # 2*200 truncated to a byte by the native DLL
    assert spec.decode(bytes.fromhex(VEC["analog_clock"]))[0] == "analog_clock"
    assert spec.decode(bytes.fromhex(VEC["rtc_text"]))[1]["fmt"] == "Y-M-D H:Q:S"
