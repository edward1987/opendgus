"""Every encoder must byte-match the DGUS editor's own C# code (tools/csharp_harness -> tests/vectors)."""
from pathlib import Path

import pytest

from opendgus.formats import controls as d

VEC = Path(__file__).parent / "vectors"
vec = dict(l.split() for l in open(VEC / "cs_vectors.txt") if l.strip())
py = {
 "basic_touch": d.basic_touch(3, (10, 20, 110, 60), 0x0031, pic_on=5),
 "return_key": d.return_key(1, (0, 0, 200, 100), 0x5000, 0x5A03, vp_mode=0x10, hold_time=3, pic_next=2),
 "return_key_fd_ivr": d.return_key(0x105, (5, 6, 7, 8), 0x1234, 1, auto_upload=False, ivr_code=3),
 "var_input": d.var_input(4, (100, 100, 300, 140), 0x5100, 1, 5, 2, (290, 105), 0xF800, 0, 16, 1, 1, 1, 9,
                          (0, 0, 900, 272), (50, 200), limits_en=0xFF, v_min=-100, v_max=100000,
                          return_set=0x5A, return_vp=0x5200, return_data=0x1234, layer_gama_pct=50),
 "text_input": d.text_input(6, (10, 10, 400, 50), 0x6000, 20, 1, 0, 8, 16, 1, 0x001F, (12, 12), (800, 48), 0x55,
                            1, 10, (0, 200, 799, 479), (0, 240), display_en=0, layer_gama_pct=100),
 "var_icon": d.var_icon(0x5012, (30, 40), 0, 10, 1, 11, 48, mode=0, layer_mode=1, icon_gamma_pct=50,
                        pic_gamma_pct=100, filter_set=0x10, group=True, sp=0x9000),
 "data_var": d.data_var(0x5420, (100, 200), 0xFFFF, 0, 16, 1, 3, 1, 5, unit="mV", spacing_flag=1, zero_flag=1),
 "text": d.text_display(0x5020, (10, 300), 0x07E0, (10, 300, 800, 340), 40, 0, 0, 12, 24, 2, h_align=2,
                        v_align=1, spacing_flag=True, hor_dis=1, ver_dis=2, sp=0x8800),
}


@pytest.mark.parametrize("name", sorted(py))
def test_record_matches_csharp(name):
    assert py[name].hex().upper() == vec[name]


def test_build_14_matches_csharp():
    ic2 = d.var_icon(0x5000, (0, 0), 0, 1, 0, 1, 48)
    pages = {0: [ic2, py["data_var"]], 2: [py["text"]]}
    cs14 = (VEC / "cs_14.bin").read_bytes()
    assert d.build_14(pages) == cs14
    assert d.parse_14(cs14) == pages


def test_parse_13_roundtrip():
    recs = [py["basic_touch"], py["return_key"], py["var_input"], py["text_input"]]
    assert d.parse_13(d.build_13(recs)) == recs
