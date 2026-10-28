"""Graphics / special display specs must reproduce the C# vectors (tests/vectors/graphics.txt) and decode back."""
from pathlib import Path

import pytest

import opendgus.formats.specs  # noqa: F401  (fills the registry)
from opendgus.formats import spec

VEC_FILE = Path(__file__).parent / "vectors" / "graphics.txt"
VEC = dict(line.split() for line in VEC_FILE.read_text().splitlines() if line.strip()) if VEC_FILE.exists() else {}

# Same inputs as tools/csharp_harness/families/graphics.cs, expressed as spec fields
CASES = {
    "curve": ("curve", dict(sp=0x9400, move_dir=1, display_mode=True, x1=10, y1=20, x2=790, y2=460, y_central=240,
                            vd_central=0x8000, color=0xF800, mul_y=0x0180, channel=3, dis_hor=2, pixel_scale=1)),
    "curve_colorvp_clamp": ("curve", dict(color_from_vp=True, color=0x5600, x1=0, y1=0, x2=800, y2=480,
                                          y_central=100, vd_central=0, mul_y=0x0100, channel=7, dis_hor=1)),
    "basic_graphics": ("basic_graphics", dict(vp=0x6000, x1=5, y1=6, x2=400, y2=300, dashed=True, dash1=4, dash2=2,
                                              dash3=6, dash4=3)),
    "basic_graphics_clamp": ("basic_graphics", dict(sp=0x9500, vp=0x6100, x1=0, y1=0, x2=1000, y2=480)),
    "table": ("table", dict(vp=0x7000, cols=4, rows=5, col_start=1, row_start=2, unit_len=8, encode_mode=2,
                            border=True, auto_format=False, char_spacing=True, x1=10, y1=10, x2=900, y2=470,
                            line_color=0x8410, color=0x001F, font0=1, font1=2, font_x=8, font_y=16, col_adjust=3)),
    "progress_bar": ("progress_bar", dict(sp=0x9600, vp=0x5100, x1=20, y1=400, x2=620, y2=430, border_color=0xFFFF,
                                          fore_color=0x07E0, back_color=0x2104, v_max=1000, v_min=-50,
                                          show_rate=True, fill_back=False, show_border=True, direction=1,
                                          var_type=5, vp_rate=0x5102)),
    "progress_bar_plain": ("progress_bar", dict(vp=0x5110, x1=0, y1=0, x2=30, y2=200, border_color=0,
                                                fore_color=0, back_color=0, v_max=100, v_min=0, fill_back=True,
                                                show_border=False, vp_rate=0x2222)),
    "zone_scroll": ("zone_scroll", dict(vp=0x5200, x1=100, y1=50, x2=900, y2=500, dis_move=3, mode_move=2)),
    "zone_scroll_2": ("zone_scroll", dict(sp=0x9700, vp=0x5210, x1=0, y1=0, x2=799, y2=100, dis_move=0x0102,
                                          mode_move=1)),
    "qr_code": ("qr_code", dict(vp=0x5300, x=300, y=100, unit_pixels=5, fix_mode=1, use_colors=True,
                                color0=0xFFE0, color1=0x001F)),
    "zone_brightness": ("zone_brightness", dict(vp=0x5400, x1=10, y1=20, x2=810, y2=470)),
    "data_transmit": ("data_transmit", dict(vp=0x5500, auto_upload=True, x1=10, y1=20, x2=110, y2=60,
                                            data="5AA5048301000ab")),
    "data_transmit_full": ("data_transmit", dict(sp=0x9800, vp=0x5510, x1=1, y1=2, x2=3, y2=4,
                                                 data="01ZZ0203040506070809101112FF")),
    "video": ("video", dict(vp=0x5600, x=80, y=40, width=640, height=400, fps=30, type=0, icl_id=50, wae_id=51)),
    "camera": ("camera", dict(vp=0x3000, x=0, y=0, width=640, height=480, camera_id=1, light=True, mirror=True,
                              light_set=40, resolution=2, display_scale=1)),
    "camera_vp_clamp": ("camera", dict(sp=0x9900, vp=0x1000, x=10, y=10, width=320, height=240, mirror=True,
                                       light_set=0)),
}

needs_vectors = pytest.mark.skipif(not VEC, reason="run tools/csharp_harness/build.sh")


@needs_vectors
def test_every_vector_has_a_case():
    assert set(VEC) == set(CASES)


@needs_vectors
@pytest.mark.parametrize("vec", sorted(CASES))
def test_spec_matches_csharp(vec):
    key, vals = CASES[vec]
    assert spec.encode(key, **vals).hex().upper() == VEC[vec]


@needs_vectors
@pytest.mark.parametrize("vec", sorted(CASES))
def test_decode_roundtrip(vec):
    raw = bytes.fromhex(VEC[vec])
    key, vals = spec.decode(raw)
    assert key == CASES[vec][0]
    assert spec.encode(key, **vals) == raw


def test_shared_type_codes_are_disambiguated():
    assert spec.decode(spec.encode("video"))[0] == "video"
    assert spec.decode(spec.encode("camera"))[0] == "camera"
    legacy_stub = bytes.fromhex("5A23FFFF0001") + bytes(26)       # BaseApply, Len 1: not a progress bar
    assert spec.identify(legacy_stub) is None or spec.identify(legacy_stub).key != "progress_bar"


def test_data_transmit_rejects_too_much_data():
    with pytest.raises(ValueError):
        spec.encode("data_transmit", data="00" * 15)
