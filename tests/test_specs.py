"""Spec-driven encoders must reproduce the C# vectors and the hand-written encoders, and decode back."""
from pathlib import Path

import pytest

import opendgus.formats.specs  # noqa: F401  (fills the registry)
from opendgus.formats import controls as legacy
from opendgus.formats import spec

VEC = dict(line.split() for line in (Path(__file__).parent / "vectors" / "cs_vectors.txt").read_text().splitlines()
           if line.strip())

# Same inputs as harness_main.cs, expressed as spec fields
CASES = {
    "basic_touch": ("basic_touch", dict(page=3, x1=10, y1=20, x2=110, y2=60, pic_on=5, key_code=0x0031)),
    "return_key": ("return_key", dict(page=1, x1=0, y1=0, x2=200, y2=100, pic_next=2, vp=0x5000, vp_mode=0x10,
                                      key_code=0x5A03, hold_time=3)),
    "return_key_fd_ivr": ("return_key", dict(page=0x105, ivr_code=3, x1=5, y1=6, x2=7, y2=8, vp=0x1234, key_code=1,
                                             auto_upload=False)),
    "var_input": ("var_input", dict(page=4, x1=100, y1=100, x2=300, y2=140, vp=0x5100, var_type=1, n_int=5, n_dot=2,
                                    show_x=290, show_y=105, color=0xF800, lib_id=0, font_hor=16, cursor_color=1,
                                    hide_en=1, kb_source=1, pic_kb=9, kb_x1=0, kb_y1=0, kb_x2=900, kb_y2=272,
                                    kb_pos_x=50, kb_pos_y=200, limits_en=0xFF, v_min=-100, v_max=100000,
                                    return_set=0x5A, return_vp=0x5200, return_data=0x1234, layer_gamma=50)),
    "text_input": ("text_input", dict(page=6, x1=10, y1=10, x2=400, y2=50, vp=0x6000, vp_len_max=20, scan_mode=1,
                                      lib_id=0, font_hor=8, font_ver=16, cursor_color=1, color=0x001F, scan_x1=12,
                                      scan_y1=12, scan_x2=800, scan_y2=48, scan_return_mode=0x55, kb_source=1,
                                      pic_kb=10, kb_x1=0, kb_y1=200, kb_x2=799, kb_y2=479, kb_pos_x=0, kb_pos_y=240,
                                      display_en=0, layer_gamma=100)),
    "var_icon": ("var_icon", dict(sp=0x9000, vp=0x5012, x=30, y=40, v_min=0, v_max=10, icon_min=1, icon_max=11,
                                  icon_lib=48, mode=0, layer_mode=1, icon_gamma=50, pic_gamma=100, filter_set=0x10,
                                  group=True)),
    "data_var": ("data_var", dict(vp=0x5420, x=100, y=200, color=0xFFFF, lib_id=0, font_x=16, spacing_flag=True,
                                  zero_flag=True, align=1, n_int=3, n_dot=1, var_type=5, unit_len=2, unit="mV")),
    "text": ("text_display", dict(sp=0x8800, vp=0x5020, x=10, y=300, color=0x07E0, x1=10, y1=300, x2=800, y2=340,
                                  text_len=40, font0=0, font1=0, font_x=12, font_y=24, encode_mode=2, h_align=2,
                                  v_align=1, spacing_flag=True, hor_dis=1, ver_dis=2)),
}


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


def test_inc_adjust_and_art_var_match_legacy():
    a = legacy.inc_adjust(1, (10, 20, 30, 40), 0x5010, increase=False, wrap=False, step=5, v_min=160, v_max=300,
                          key_once=False, pic_on=2)
    b = spec.encode("inc_adjust", page=1, x1=10, y1=20, x2=30, y2=40, vp=0x5010, increase=False, wrap=False,
                    step=5, v_min=160, v_max=300, key_once=False, pic_on=2)
    assert a == b
    a = legacy.art_var(0x5011, (808, 188), 40, 48, 2, 1, align=1, show_zeros=True)
    b = spec.encode("art_var", vp=0x5011, x=808, y=188, icon0=40, icon_lib=48, n_int=2, n_dot=1, align=1,
                    show_zeros=True)
    assert a == b


def test_unknown_field_rejected():
    with pytest.raises(TypeError):
        spec.encode("var_icon", colour=1)


def test_every_spec_has_valid_layout():
    for s in spec.REGISTRY.values():
        assert s.length in (16, 32, 48, 64)
        used = {}
        for f in s.fields:
            for o in range(f.offset, f.offset + f.nbytes):
                assert o < s.length, f"{s.key}.{f.name} past end"
                if s.kind == "touch":
                    assert o >= 0x10 and o % 16 != 0, f"{s.key}.{f.name} overlaps header/0xFE marker"
                else:
                    assert o >= 6, f"{s.key}.{f.name} overlaps display header"
                if not f.bits:
                    assert o not in used, f"{s.key}.{f.name} overlaps {used.get(o)}"
                    used[o] = f.name
        assert spec.schema(s.key)["properties"]
