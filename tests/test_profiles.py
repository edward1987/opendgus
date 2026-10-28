import pytest

from opendgus.profiles import PROFILES, custom, decode_part_number


def test_known_profiles_consistent():
    for p in PROFILES.values():
        assert p.background_icl == (32 if p.flash_mb == 16 else 23)
        assert p.slots in (32, 64)
        assert p.width > 0 and p.height > 0


@pytest.mark.parametrize("pn,w,h,touch", [
    ("DMG10600C070_03WTC", 1024, 600, "C"),      # the unit verified in this project
    ("DMG80480C043_03WTR", 800, 480, "R"),
    ("DMG12800C070_03WTC", 800, 1280, "C"),      # portrait panel
    ("DMG85480C050_03WN", 480, 854, "C"),         # profile lookup wins (touch from table)
    ("DMG64480C057_03WTC", 640, 480, "C"),        # not in table: decoded
])
def test_decode_part_number(pn, w, h, touch):
    p = decode_part_number(pn)
    assert (p.width, p.height) == (w, h)


def test_cof_defaults_to_8mb_and_slot_23():
    p = decode_part_number("DMG48270F043_01WTC")
    assert p.flash_mb == 8 and p.background_icl == 23 and p.cpu == "T5L0"


def test_custom_cpu_choice():
    assert custom(480, 272).cpu == "T5L1"
    assert custom(1280, 800).cpu == "T5L2"
    assert custom(1280, 800).jpeg_limit > custom(480, 272).jpeg_limit


def test_bad_part_number():
    with pytest.raises(ValueError):
        decode_part_number("XYZ123")
