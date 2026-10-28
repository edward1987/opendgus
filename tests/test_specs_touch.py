"""Touch-family specs (13.bin) must reproduce the C# vectors in tests/vectors/touch.txt and decode back."""
from pathlib import Path

import pytest

import opendgus.formats.specs  # noqa: F401  (fills the registry)
from opendgus.formats import spec

VEC = dict(line.split() for line in (Path(__file__).parent / "vectors" / "touch.txt").read_text().splitlines()
           if line.strip())


def H(page, x1, y1, x2, y2, nxt=-1, on=-1, **kw):
    return dict(page=page, x1=x1, y1=y1, x2=x2, y2=y2, pic_next=nxt, pic_on=on, **kw)


# Same inputs as tools/csharp_harness/families/touch.cs, expressed as spec fields
CASES = {
    "inc_adjust": ("inc_adjust", H(2, 10, 20, 60, 70, -1, 3, vp=0x5010, vp_mode=0x13, increase=True, wrap=True,
                                   step=5, v_min=-10, v_max=300, key_once=False, key_delay=7)),
    "inc_adjust_fd": ("inc_adjust", H(0x123, 0, 0, 800, 480, 4, -1, auto_upload=False, vp=0x1000, increase=False,
                                      step=1, v_min=0, v_max=1, key_once=True)),
    "popup_menu": ("popup_menu", H(1, 100, 100, 200, 140, vp=0x5100, vp_mode=2, pic_menu=12, menu_x1=100,
                                   menu_y1=50, menu_x2=900, menu_y2=500, menu_pos_x=300, menu_pos_y=600,
                                   layer_gamma=40)),
    "popup_menu_fd": ("popup_menu", H(5, 1, 2, 3, 4, 6, 7, auto_upload=False, vp=0x2000, vp_mode=0x1F,
                                      pic_menu=0x105, menu_x1=10, menu_y1=20, menu_x2=300, menu_y2=200,
                                      menu_pos_x=799, menu_pos_y=10, layer_gamma=100)),
    "drag_adjust_h": ("drag_adjust", H(3, 0, 0, 1, 1, vp=0x5200, vp_mode=1, direction=0, adj_x1=20, adj_y1=100,
                                       adj_x2=780, adj_y2=140, v_begin=-50, v_end=1000)),
    "drag_adjust_v": ("drag_adjust", H(3, 0, 0, 1, 1, 2, 9, vp=0x5202, vp_mode=2, direction=1, adj_x1=400,
                                       adj_y1=10, adj_x2=440, adj_y2=470, v_begin=100, v_end=0)),
    "drag_adjust_clamped": ("drag_adjust", H(3, 0, 0, 1, 1, auto_upload=False, vp=0x5204, adj_x1=100, adj_y1=300,
                                             adj_x2=900, adj_y2=600, v_begin=0, v_end=255)),
    "rtc_input": ("rtc_input", H(4, 50, 60, 250, 90, -1, 8, show_x=100, show_y=200, color=0xF800, lib_id=3,
                                 font_hor=12, cursor_color=1, kb_source=1, pic_kb=7, kb_x1=0, kb_y1=10, kb_x2=820,
                                 kb_y2=300, kb_pos_x=50, kb_pos_y=500)),
    "gbk_input": ("gbk_input", H(6, 10, 10, 400, 50, vp=0x6000, vp_len_max=30, scan_mode=1, lib_gbk1=0,
                                 lib_gbk2=24, font_scale1=16, font_scale2=24, cursor_color=1, color0=0x001F,
                                 color1=0xFFE0, py_disp_mode=1, scan_return_mode=0x55, scan_x1=12, scan_y1=12,
                                 scan_x2=398, scan_y2=48, hint_x=20, hint_y=60, scan_dis=4, kb_source=1, pic_kb=11,
                                 kb_x1=0, kb_y1=200, kb_x2=900, kb_y2=479, kb_pos_x=0, kb_pos_y=240)),
    "param_config": ("param_config", H(7, 0, 0, 100, 100, vp_mode=0x5A, data_pack="0102A0FF5500000000000000007E")),
    "param_config_odd": ("param_config", H(7, 0, 0, 100, 100, 1, auto_upload=False, vp_mode=1, data_pack="ABC")),
    "sync_return": ("sync_return", H(8, 30, 40, 130, 90, 9, press_mode=0x5A, press_src=0x5300, press_dst=0x5400,
                                     press_len=4, hold_mode=0x5A, hold_src=0x5301, hold_dst=0x5401, hold_len=2,
                                     release_mode=0, release_src=0x5302, release_dst=0x5402, release_len=1)),
    "rotate_adjust": ("rotate_adjust", H(9, 200, 100, 400, 300, vp=0x5500, vp_mode=2, center_x=300, center_y=200,
                                         r0=40, r1=100, a0=90, a1=630, v_begin=-100, v_end=100)),
    "swipe_adjust": ("swipe_adjust", H(10, 0, 100, 800, 200, vp=0x5600, direction=1, step_dis=20)),
    "swipe_page_h": ("swipe_page", H(11, 0, 50, 800, 470, pic_prev=10, pic_next_page=12, vertical=False,
                                     upload_page=1, push_speed=5, push_dis=300, end_animation=1)),
    "swipe_page_v": ("swipe_page", H(11, 20, 0, 900, 480, auto_upload=False, pic_prev=0x101, pic_next_page=2,
                                     vertical=True, upload_page=0, push_speed=10, push_dis=0x1234,
                                     end_animation=0)),
    "slide_icon_select": ("slide_icon_select", H(12, 0, 300, 800, 400, 5, 6, vp=0x5700, direction=1, icon_id=13,
                                                 speed=3)),
    "bit_button": ("bit_button", H(13, 10, 10, 60, 60, -1, 14, auto_upload=False, vp=0x5800, bit_pos=15, mode=2)),
    "bit_button_fe": ("bit_button", H(13, 10, 10, 60, 60, auto_upload=True, vp=0x5801, bit_pos=3, mode=3)),
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


def test_touch_specs_csharp_verified():
    for key in ("popup_menu", "drag_adjust", "rtc_input", "gbk_input", "param_config", "sync_return",
                "rotate_adjust", "swipe_adjust", "swipe_page", "slide_icon_select", "bit_button"):
        s = spec.REGISTRY[key]
        assert s.kind == "touch" and s.verified == "csharp"


def test_gbk_and_text_input_share_fe06():
    gbk = spec.encode("gbk_input", vp=0x6000)
    txt = spec.encode("text_input", vp=0x6000)
    assert gbk[14:16] == txt[14:16] == b"\xFE\x06"
    assert gbk[63] == 0x02 and txt[63] != 0x02
    assert spec.decode(gbk)[0] == "gbk_input"
    assert spec.decode(txt)[0] == "text_input"


def test_sync_return_is_always_fe():
    b = spec.encode("sync_return", auto_upload=False)
    assert b[14:16] == b"\xFE\x08" and b[0x10] == b[0x18] == b[0x20] == 0xFE


def test_drag_adjust_derives_touch_area():
    b = spec.encode("drag_adjust", x1=1, y1=2, x2=3, y2=4, adj_x1=10, adj_y1=50, adj_x2=790, adj_y2=90)
    assert [int.from_bytes(b[i:i + 2], "big") for i in range(2, 10, 2)] == [0, 50, 800, 90]
    b = spec.encode("drag_adjust", direction=1, adj_x1=10, adj_y1=50, adj_x2=40, adj_y2=470)
    assert [int.from_bytes(b[i:i + 2], "big") for i in range(2, 10, 2)] == [10, 18, 40, 480]


def test_slide_icon_select_forces_ffff():
    b = spec.encode("slide_icon_select", pic_next=3, pic_on=4)
    assert b[10:14] == b"\xFF" * 4


def test_param_config_hex_pack():
    b = spec.encode("param_config", data_pack="01 02 0A")
    assert b[0x12:0x20] == bytes([1, 2, 10]) + bytes(11)
    assert spec.decode(b)[1]["data_pack"] == "01020A"
    with pytest.raises(ValueError):
        spec.encode("param_config", data_pack="00" * 15)


def test_swipe_page_band_follows_touch_area():
    b = spec.encode("swipe_page", x1=0, y1=40, x2=800, y2=480)
    assert b[0x15:0x19] == (40).to_bytes(2, "big") + (479).to_bytes(2, "big")
