"""Tests for the slice 4 obligations in CONTRACT.md.

Slice 4 reads the collection naming settings of the analysed
project. The selector honours python_functions and python_classes,
discovery honours python_files, and the report names any non
default settings in force. Every fixture here is synthetic and
written for this test file.
"""

import json

from ostensible.report import to_json, to_text
from ostensible.runner import _discover, analyse_project
from ostensible.settings import (
    CollectionSettings,
    file_matches,
    load_collection_settings,
    name_matches,
)
from ostensible.static_scan import selectable_test_items
from factories import WELL_TESTED, write_project


# F1, the settings are read from the one winning source.


def test_pytest_ini_wins_over_pyproject(tmp_path):
    project = write_project(
        tmp_path / "precedence",
        {
            "pytest.ini": "[pytest]\npython_functions = check_*\n",
            "pyproject.toml": (
                "[tool.pytest.ini_options]\n"
                'python_functions = ["verify_*"]\n'
            ),
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*",)


def test_pyproject_ini_options_are_read(tmp_path):
    project = write_project(
        tmp_path / "toml",
        {
            "pyproject.toml": (
                "[tool.pytest.ini_options]\n"
                'python_functions = ["check_*", "verify_*"]\n'
                'python_classes = ["Check*"]\n'
            ),
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*", "verify_*")
    assert settings.python_classes == ("Check*",)
    assert settings.python_files is None


def test_pyproject_without_the_table_falls_through(tmp_path):
    project = write_project(
        tmp_path / "fallthrough",
        {
            "pyproject.toml": '[project]\nname = "fixture"\n',
            "setup.cfg": "[tool:pytest]\npython_files = checks_*.py\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_files == ("checks_*.py",)


def test_tox_ini_wins_over_setup_cfg(tmp_path):
    project = write_project(
        tmp_path / "setupcfg",
        {
            "setup.cfg": "[tool:pytest]\npython_classes = Check*\n",
            "tox.ini": "[pytest]\npython_classes = Verify*\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_classes == ("Verify*",)


def test_tox_ini_is_read_when_it_is_the_only_source(tmp_path):
    project = write_project(
        tmp_path / "toxini",
        {"tox.ini": "[pytest]\npython_functions = check_*\n"},
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*",)


def test_setup_cfg_without_the_section_is_not_a_source(tmp_path):
    project = write_project(
        tmp_path / "nosection",
        {
            "setup.cfg": "[metadata]\nname = fixture\n",
            "tox.ini": "[pytest]\npython_functions = check_*\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*",)


def test_ini_values_split_on_whitespace_and_lines(tmp_path):
    project = write_project(
        tmp_path / "multiline",
        {
            "pytest.ini": (
                "[pytest]\n"
                "python_functions =\n"
                "    check_*\n"
                "    verify_*\n"
            ),
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*", "verify_*")


def test_a_project_with_no_source_reads_the_defaults(tmp_path):
    project = write_project(tmp_path / "plain", {"calc.py": "x = 1\n"})
    settings = load_collection_settings(project)
    assert settings == CollectionSettings()


def test_a_broken_source_contributes_nothing_and_blocks_later(
    tmp_path,
):
    project = write_project(
        tmp_path / "broken",
        {
            "pyproject.toml": "[tool.pytest.ini_options\n",
            "setup.cfg": "[tool:pytest]\npython_files = checks_*.py\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings == CollectionSettings()


# F2, pattern matching in the pytest sense.


def test_name_matches_by_prefix_or_by_glob():
    assert name_matches("check_adds", ("check",))
    assert name_matches("verify_total", ("verify_*",))
    assert not name_matches("test_adds", ("check_*",))
    assert not name_matches("check_adds", ())


def test_file_matches_the_name_alone_as_a_glob():
    assert file_matches(
        "checks_calc.py", "checks_calc.py", ("checks_*.py",)
    )
    assert not file_matches(
        "test_calc.py", "test_calc.py", ("checks_*.py",)
    )


# F3, the selector honours the function and class settings.


def test_custom_function_patterns_replace_the_default_prefix():
    source = (
        "def check_adds():\n"
        "    pass\n"
        "\n"
        "\n"
        "def test_other():\n"
        "    pass\n"
    )
    settings = CollectionSettings(python_functions=("check_*",))
    assert selectable_test_items(source, settings) == ["check_adds"]
    assert selectable_test_items(source) == ["test_other"]


def test_custom_glob_pattern_selects_matching_functions():
    source = (
        "def verify_total():\n"
        "    pass\n"
        "\n"
        "\n"
        "def check_total():\n"
        "    pass\n"
    )
    settings = CollectionSettings(python_functions=("verify_*",))
    assert selectable_test_items(source, settings) == ["verify_total"]


def test_an_empty_function_setting_selects_nothing():
    source = "def test_adds():\n    pass\n"
    settings = CollectionSettings(python_functions=())
    assert selectable_test_items(source, settings) == []


def test_custom_class_patterns_replace_the_default_prefix():
    source = (
        "import unittest\n"
        "\n"
        "\n"
        "class TestPlain:\n"
        "    def test_a(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class CheckPlain:\n"
        "    def test_b(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class Cases(unittest.TestCase):\n"
        "    def test_c(self):\n"
        "        pass\n"
    )
    settings = CollectionSettings(python_classes=("Check*",))
    assert selectable_test_items(source, settings) == [
        "CheckPlain::test_b",
        "Cases::test_c",
    ]


def test_method_names_follow_the_function_setting():
    source = (
        "class TestCalc:\n"
        "    def check_adds(self):\n"
        "        pass\n"
        "\n"
        "    def test_other(self):\n"
        "        pass\n"
    )
    settings = CollectionSettings(python_functions=("check_*",))
    assert selectable_test_items(source, settings) == [
        "TestCalc::check_adds"
    ]


def test_collectability_refusals_hold_under_custom_patterns():
    source = (
        "class CheckInit:\n"
        "    def __init__(self):\n"
        "        self.value = 1\n"
        "\n"
        "    def test_a(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class CheckOff:\n"
        "    __test__ = False\n"
        "\n"
        "    def test_b(self):\n"
        "        pass\n"
    )
    settings = CollectionSettings(python_classes=("Check*",))
    assert selectable_test_items(source, settings) == []


# F4, discovery honours the file setting.


def _names(paths):
    return sorted(path.name for path in paths)


def test_discovery_honours_python_files(tmp_path):
    project = write_project(
        tmp_path / "discovery",
        {
            "calc.py": "def add_one(x):\n    return x + 1\n",
            "test_calc.py": "def test_adds():\n    pass\n",
            "checks_calc.py": "def test_adds():\n    pass\n",
        },
    )
    settings = CollectionSettings(python_files=("checks_*.py",))
    test_files, sources = _discover(project, settings)
    assert _names(test_files) == ["checks_calc.py"]
    assert _names(sources) == ["calc.py", "test_calc.py"]
    test_files, sources = _discover(project)
    assert _names(test_files) == ["test_calc.py"]
    assert _names(sources) == ["calc.py", "checks_calc.py"]


# The headline proofs, run end to end through the analysis.

CUSTOM_FUNCTIONS = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from unittest.mock import Mock\n"
        "\n"
        "from calc import add_one\n"
        "\n"
        "\n"
        "def check_adds():\n"
        "    assert add_one(1) == 2\n"
        "    assert add_one(0) == 1\n"
        "\n"
        "\n"
        "def check_fetch_returns_what_it_was_told():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 42\n"
    ),
    "pyproject.toml": (
        "[tool.pytest.ini_options]\n"
        'python_functions = ["check_*"]\n'
    ),
}


def test_custom_function_prefix_project_is_judged_per_item(tmp_path):
    project = write_project(tmp_path / "customfn", CUSTOM_FUNCTIONS)
    analysis = analyse_project(project, timeout=60)
    (verdict,) = analysis.verdicts
    by_name = {item.name: item.status for item in verdict.functions}
    assert by_name == {
        "check_adds": "can_fail",
        "check_fetch_returns_what_it_was_told": "decorative_candidate",
    }
    assert verdict.whole_file is False
    assert verdict.status == "can_fail"
    assert analysis.collection_settings == {
        "python_functions": ["check_*"]
    }
    data = json.loads(to_json(analysis))
    assert data["collection_settings"] == {
        "python_functions": ["check_*"]
    }
    assert (
        "collection settings - python_functions check_*"
        in to_text(analysis)
    )


def test_the_same_project_without_settings_falls_back(tmp_path):
    files = {
        name: content
        for name, content in CUSTOM_FUNCTIONS.items()
        if name != "pyproject.toml"
    }
    project = write_project(tmp_path / "nosettings", files)
    analysis = analyse_project(project, timeout=60)
    (verdict,) = analysis.verdicts
    assert verdict.whole_file is True
    assert verdict.no_tests is True
    assert verdict.status == "no_applicable_mutants"
    assert analysis.collection_settings == {}
    data = json.loads(to_json(analysis))
    assert "collection_settings" not in data
    assert "collection settings" not in to_text(analysis)


CUSTOM_CLASSES = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from calc import add_one\n"
        "\n"
        "\n"
        "class CheckAdd:\n"
        "    def test_adds(self):\n"
        "        assert add_one(1) == 2\n"
        "        assert add_one(0) == 1\n"
    ),
    "pytest.ini": "[pytest]\npython_classes = Check*\n",
}


def test_custom_class_prefix_project_is_judged_per_method(tmp_path):
    project = write_project(tmp_path / "customclass", CUSTOM_CLASSES)
    analysis = analyse_project(project, timeout=60)
    (verdict,) = analysis.verdicts
    assert [item.name for item in verdict.functions] == [
        "CheckAdd::test_adds"
    ]
    assert verdict.functions[0].status == "can_fail"
    assert verdict.whole_file is False
    data = json.loads(to_json(analysis))
    assert data["collection_settings"] == {
        "python_classes": ["Check*"]
    }


CUSTOM_FILES = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "checks_calc.py": (
        "from calc import add_one\n"
        "\n"
        "\n"
        "def test_adds():\n"
        "    assert add_one(1) == 2\n"
        "    assert add_one(0) == 1\n"
    ),
    "setup.cfg": "[tool:pytest]\npython_files = checks_*.py\n",
}


def test_custom_file_pattern_project_is_discovered_and_judged(
    tmp_path,
):
    project = write_project(tmp_path / "customfiles", CUSTOM_FILES)
    analysis = analyse_project(project, timeout=60)
    (verdict,) = analysis.verdicts
    assert verdict.path == "checks_calc.py"
    assert [item.name for item in verdict.functions] == ["test_adds"]
    assert verdict.functions[0].status == "can_fail"
    data = json.loads(to_json(analysis))
    assert data["collection_settings"] == {
        "python_files": ["checks_*.py"]
    }


def test_a_default_project_gains_no_settings_entry(tmp_path):
    project = write_project(tmp_path / "welltested", WELL_TESTED)
    analysis = analyse_project(project, timeout=60)
    data = json.loads(to_json(analysis))
    assert "collection_settings" not in data
    assert "collection settings" not in to_text(analysis)
