"""Icon-family specs must reproduce the editor's GetData() bytes (tests/vectors/icons.txt) and decode back."""
from pathlib import Path

import pytest

import opendgus.formats.specs  # noqa: F401  (fills the registry)
from opendgus.formats import spec

_VF = Path(__file__).parent / "vectors" / "icons.txt"
VEC = dict(line.split() for line in _VF.read_text().splitlines() if line.strip()) if _VF.exists() else {}

# Same inputs as tools/csharp_harness/families/icons.cs, expressed as spec fields
CASES = {
    "animation_icon": ("animation_icon", dict(sp=0x9100, vp=0x5030, x=120, y=64, restart_first=1, v_stop=0, v_start=1,
                                              icon_stop=5, icon_start=6, icon_end=20, icon_lib=40, mode=0,
                                              layer_mode=2, icon_gamma=60, pic_gamma=30, frame_time=25, play_once=1,
                                              filter_set=0x20)),
    "animation_icon_clamp": ("animation_icon", dict(vp=0x5031, x=900, y=480, v_start=0, icon_start=0, icon_end=3,
                                                    icon_lib=23, mode=1, frame_time=1)),
    "slider_display": ("slider_display", dict(vp=0x5040, v_begin=-50, v_end=300, x_begin=100, x_end=700, icon=7,
                                              y=200, x_adj=12, vertical=1, icon_lib=41, mode=1, vp_mode=2,
                                              layer_mode=1, icon_gamma=100, pic_gamma=50, filter_set=3)),
    "art_var": ("art_var", dict(sp=0x9200, vp=0x5011, x=808, y=188, icon0=40, icon_lib=48, mode=1, n_int=2, n_dot=1,
                                var_type=5, align=1, show_zeros=True, layer_mode=2, icon_gamma=50, pic_gamma=25,
                                filter_set=0x3F)),
    "image_animation": ("image_animation", dict(pic_begin=10, pic_end=0x123, frame_time=12, icl_lib=33,
                                                pic_end_exp=0x0204)),
    "icon_rotation": ("icon_rotation", dict(sp=0x9300, vp=0x5050, icon=3, icon_xc=50, icon_yc=60, xc=400, yc=240,
                                            v_begin=-100, v_end=1000, al_begin=0, al_end=540, vp_mode=1, icon_lib=44,
                                            mode=1, filter_set=7)),
    "bit_icon": ("bit_icon", dict(vp=0x5060, vp_aux=0x5100, act_bits=0x00F0, display_mode=3, move_mode=1, mode=1,
                                  icon_lib=45, icon0s=1, icon0e=4, icon1s=5, icon1e=8, x=810, y=100, dis_mov=40,
                                  filter_set=9)),
    "icon_page_trans": ("icon_page_trans", dict(vp=0x5070, icon_lib=46, mode=1, filter_set=2, vertical=1, icon=9,
                                                x1=10, y1=20, x2=410, y2=220)),
    "icon_overlay": ("icon_overlay", dict(sp=0x9400, vp=0x5080, x=30, y=40, width=200, height=150, dim=200, mode=1,
                                          filter_set=4, reverse_order=True, vp_page=0x22)),
    "batch_icon": ("batch_icon", dict(vp=0x5090, vp_pos=0x5100, vp_icons=0x5200, count=16, source=1, icon_lib=47,
                                      icon=12, x1=20, y1=30, x2=320, y2=130)),
    "multi_language": ("multi_language", dict(sp=0x9500, vp=0x50A0, x=5, y=6, v_min=0, v_max=3, icon_min=10,
                                              icon_max=13, icon_lib=49, mode=1, layer_mode=1, icon_gamma=80,
                                              pic_gamma=20, filter_set=1)),
}

pytestmark = pytest.mark.skipif(not VEC, reason="tests/vectors/icons.txt missing (run tools/csharp_harness/build.sh)")


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


def test_var_icon_and_multi_language_are_told_apart():
    assert spec.decode(spec.encode("var_icon", group=True))[0] == "var_icon"
    assert spec.decode(spec.encode("multi_language"))[0] == "multi_language"
