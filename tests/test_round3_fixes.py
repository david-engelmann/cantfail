"""Tests for the Round 3 review fix obligations in CONTRACT.md.

Every fixture here is synthetic and written for this test file.
The probes of the Round 3 red team are ported here as regression
tests, each checked against the behaviour of the pytest installed
on this machine where the two tools could be compared directly.
"""

import json
from pathlib import Path

from ostensible.report import to_json, to_text
from ostensible.runner import analyse_project
from ostensible.settings import (
    CollectionSettings,
    load_collection_settings,
)
from ostensible.static_scan import selectable_test_items


def write_project(root, files):
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_a_test_class_is_not_named_under_a_restrictive_class_setting():
    source = (
        "class TestWeak:\n"
        "    def test_fetch(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class CheckStrong:\n"
        "    def test_adds(self):\n"
        "        pass\n"
    )
    settings = CollectionSettings(python_classes=("Check*",))
    assert selectable_test_items(source, settings) == [
        "CheckStrong::test_adds"
    ]


def test_tox_ini_wins_and_pytest_toml_outranks_everything(tmp_path):
    project = write_project(
        tmp_path / "tomlfirst",
        {
            "pytest.toml": (
                "[pytest]\npython_functions = [\"toml_*\"]\n"
            ),
            "pytest.ini": "[pytest]\npython_functions = ini_*\n",
            "tox.ini": "[pytest]\npython_functions = tox_*\n",
            "setup.cfg": "[tool:pytest]\npython_functions = cfg_*\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("toml_*",)


def test_dot_pytest_ini_is_read(tmp_path):
    project = write_project(
        tmp_path / "dotini",
        {".pytest.ini": "[pytest]\npython_functions = dot_*\n"},
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("dot_*",)


def test_a_native_pytest_table_is_read_and_blocks_setup_cfg(tmp_path):
    project = write_project(
        tmp_path / "native",
        {
            "pyproject.toml": (
                "[tool.pytest]\npython_functions = [\"check_*\"]\n"
            ),
            "setup.cfg": (
                "[tool:pytest]\npython_functions = verify_*\n"
            ),
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*",)


def test_a_pyproject_holding_both_tables_is_a_broken_source(tmp_path):
    project = write_project(
        tmp_path / "both",
        {
            "pyproject.toml": (
                "[tool.pytest]\npython_functions = [\"check_*\"]\n"
                "[tool.pytest.ini_options]\n"
                "python_functions = \"verify_*\"\n"
            ),
            "tox.ini": "[pytest]\npython_functions = tox_*\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings == CollectionSettings()


def test_a_wrong_shaped_pyproject_yields_defaults_without_a_crash(
    tmp_path,
):
    project = write_project(
        tmp_path / "shape",
        {"pyproject.toml": 'tool = "not a table"\n'},
    )
    settings = load_collection_settings(project)
    assert settings == CollectionSettings()


def test_a_scalar_setting_value_reads_as_its_string_form(tmp_path):
    project = write_project(
        tmp_path / "scalar",
        {
            "pyproject.toml": (
                "[tool.pytest.ini_options]\npython_functions = 42\n"
            )
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("42",)


def test_a_path_carrying_file_pattern_discovers_the_file(tmp_path):
    project = write_project(
        tmp_path / "pathpat",
        {
            "setup.cfg": (
                "[tool:pytest]\npython_files = sub/checks_*.py\n"
            ),
            "calc.py": "def add(a, b):\n    return a + b\n",
            "sub/checks_calc.py": (
                "from calc import add\n"
                "\n"
                "\n"
                "def test_adds():\n"
                "    assert add(1, 2) == 3\n"
            ),
        },
    )
    result = analyse_project(project, timeout=60)
    statuses = {entry.status for entry in result.verdicts}
    assert "can_fail" in statuses


def test_restated_defaults_produce_no_disclosure(tmp_path):
    project = write_project(
        tmp_path / "restated",
        {
            "pytest.ini": (
                "[pytest]\n"
                "python_functions = test\n"
                "python_classes = Test\n"
                "python_files = test_*.py *_test.py\n"
            ),
            "calc.py": "def add(a, b):\n    return a + b\n",
            "test_calc.py": (
                "from calc import add\n"
                "\n"
                "\n"
                "def test_adds():\n"
                "    assert add(1, 2) == 3\n"
            ),
        },
    )
    result = analyse_project(project, timeout=60)
    data = json.loads(to_json(result))
    assert "collection_settings" not in data
    assert "collection settings" not in to_text(result)


def test_a_deselected_name_is_not_an_unselected_shape(tmp_path):
    project = write_project(
        tmp_path / "shapes",
        {
            "pyproject.toml": (
                "[tool.pytest.ini_options]\n"
                "python_functions = [\"check_*\"]\n"
            ),
            "calc.py": "def add(a, b):\n    return a + b\n",
            "test_calc.py": (
                "from calc import add\n"
                "\n"
                "\n"
                "def check_adds():\n"
                "    assert add(1, 2) == 3\n"
                "\n"
                "\n"
                "def test_other():\n"
                "    assert add(2, 2) == 4\n"
            ),
        },
    )
    result = analyse_project(project, timeout=60)
    (entry,) = result.verdicts
    assert entry.partial_selection is False
    assert [item.name for item in entry.functions] == ["check_adds"]
