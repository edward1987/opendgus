"""ICL / font / CRC checks. Some compare against the decompiled DGUS sources, which are local-only
(vendor/ is not redistributed), so the suite is skipped when they are missing."""
import runpy
from pathlib import Path

import pytest

DEC = Path(__file__).resolve().parents[1] / "vendor" / "decompiled" / "DwinTerminal"


@pytest.mark.skipif(not DEC.exists(), reason="needs local decompiled DGUS sources (vendor/)")
def test_asset_checks():
    runpy.run_path(str(Path(__file__).parent / "asset_checks.py"), run_name="__main__")
