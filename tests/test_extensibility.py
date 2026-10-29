from dataclasses import asdict

from opendgus.codegen.boards import BOARDS, configure_custom_boards, get
from opendgus.codegen.generate import generate
from opendgus.compiler import compile_project
from opendgus.model import BoardProfile, Control, Page, Preset, Project, Variable


def test_custom_board_uses_existing_runtime_generator():
    profile = BoardProfile.model_validate({**asdict(BOARDS["pico2"]), "id": "custom_lab_pico", "title": "Lab Pico"})
    project = Project(board_profiles=[profile])
    configure_custom_boards(project)
    assert get(profile.id).serial_setup == profile.serial_setup
    files = generate(project, profile.id)
    assert any(name.endswith(".ino") for name in files)
    configure_custom_boards(Project())
    assert profile.id not in BOARDS


def test_legacy_project_migrates_and_missing_plugin_is_reported():
    old = {"schema_version": 1, "variables": [{"name": "mode"}], "pages": [{"id": 0,
           "controls": [{"type": "acme_custom", "var": "mode", "x": 10, "y": 10}]}]}
    project = Project.model_validate(old)
    assert project.schema_version == 2 and project.presets == []
    result = compile_project(project, write=False)
    assert not result.ok
    assert any("install its OpenDGUS plugin" in issue.message for issue in result.issues)
