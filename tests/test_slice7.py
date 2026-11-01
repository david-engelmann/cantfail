"""Tests for the slice 7 obligations in CONTRACT.md.

Slice 7 walks the settings search upward from the project
folder to the filesystem root, the way pytest searches from
the common ancestor of its arguments. The first folder holding
a governing source decides, the run inside the scratch copy is
judged under the same source, and the report names where the
governing source was found.

Every fixture here is synthetic and written for this test file.
"""

import json
from pathlib import Path

from cantfail.report import to_json, to_text
from cantfail.runner import _discover, analyse_project
from cantfail.settings import (
    load_collection_settings,
    load_collection_settings_with_source,
)


def write_project(root, files):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def parent_project(tmp_path, parent_files, project_files):
    outer = write_project(tmp_path / "outer", parent_files)
    project = write_project(outer / "proj", project_files)
    return outer, project


CHECK_INI = "[pytest]\npython_functions = check_*\n"

CALC = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from calc import add_one\n"
        "\n"
        "\n"
        "def check_add_one():\n"
        "    assert add_one(1) == 2\n"
        "    assert add_one(0) == 1\n"
    ),
}


# I1, the upward search and the analysis point.


def test_a_parent_config_governs_the_settings(tmp_path):
    _outer, project = parent_project(
        tmp_path,
        {"pytest.ini": CHECK_INI},
        {"test_a.py": "def check_it():\n    assert True\n"},
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*",)


def test_the_first_folder_holding_a_source_decides(tmp_path):
    _outer, project = parent_project(
        tmp_path,
        {"pytest.ini": CHECK_INI},
        {
            "pytest.ini": (
                "[pytest]\npython_functions = verify_*\n"
            ),
            "test_a.py": "def verify_it():\n    assert True\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("verify_*",)


def test_the_search_reports_the_governing_source(tmp_path):
    outer, project = parent_project(
        tmp_path,
        {"pytest.ini": CHECK_INI},
        {"test_a.py": "def check_it():\n    assert True\n"},
    )
    _settings, source = load_collection_settings_with_source(project)
    assert source == outer / "pytest.ini"

    rooted = write_project(
        tmp_path / "rooted",
        {
            "pytest.ini": CHECK_INI,
            "test_a.py": "def check_it():\n    assert True\n",
        },
    )
    _settings, source = load_collection_settings_with_source(rooted)
    assert source == rooted / "pytest.ini"

    bare = write_project(
        tmp_path / "bare" / "proj",
        {"test_a.py": "def test_it():\n    assert True\n"},
    )
    settings, source = load_collection_settings_with_source(bare)
    assert source is None
    assert settings.python_functions is None


# I2, how the search composes across folders.


def test_a_folder_holding_no_source_decides_nothing(tmp_path):
    _outer, project = parent_project(
        tmp_path,
        {"pytest.ini": CHECK_INI},
        {
            "pyproject.toml": "[project]\nname = \"x\"\n",
            "test_a.py": "def check_it():\n    assert True\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*",)


def test_a_non_source_ini_file_decides_nothing_either(tmp_path):
    _outer, project = parent_project(
        tmp_path,
        {"pytest.ini": CHECK_INI},
        {
            "tox.ini": "[tox]\nskipsdist = true\n",
            "test_a.py": "def check_it():\n    assert True\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*",)


def test_a_broken_source_in_the_deciding_folder_ends_the_search(
    tmp_path,
):
    _outer, project = parent_project(
        tmp_path,
        {"pytest.ini": CHECK_INI},
        {
            "pytest.toml": "[pytest\nbroken = = =\n",
            "test_a.py": "def check_it():\n    assert True\n",
        },
    )
    settings, source = load_collection_settings_with_source(project)
    assert settings.python_functions is None
    assert source == project / "pytest.toml"


def test_a_broken_source_above_a_valid_one_is_never_read(tmp_path):
    _outer, project = parent_project(
        tmp_path,
        {"pytest.toml": "[pytest\nbroken = = =\n"},
        {
            "pytest.ini": CHECK_INI,
            "test_a.py": "def check_it():\n    assert True\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_functions == ("check_*",)


# I6, no source anywhere gives the defaults.


def test_no_source_anywhere_gives_the_defaults(tmp_path):
    project = write_project(
        tmp_path / "bare" / "proj",
        {"test_a.py": "def test_it():\n    assert True\n"},
    )
    settings = load_collection_settings(project)
    assert settings.python_functions is None
    assert settings.python_classes is None
    assert settings.python_files is None


# I1 and I3, a parent config names the items and the run agrees.


def test_a_parent_config_names_the_items_of_the_project(tmp_path):
    _outer, project = parent_project(
        tmp_path, {"pytest.ini": CHECK_INI}, CALC
    )
    analysis = analyse_project(project)
    assert len(analysis.verdicts) == 1
    verdict = analysis.verdicts[0]
    assert verdict.path == "test_calc.py"
    assert verdict.test_functions == ["check_add_one"]
    assert verdict.whole_file is False


def test_the_run_inside_the_copy_reads_the_parent_settings(tmp_path):
    _outer, project = parent_project(
        tmp_path, {"pytest.ini": CHECK_INI}, CALC
    )
    analysis = analyse_project(project)
    function = analysis.verdicts[0].functions[0]
    assert function.name == "check_add_one"
    assert function.baseline_ok is True
    assert function.status == "can_fail"


def test_the_whole_file_path_also_carries_the_source(tmp_path):
    files = {
        "calc.py": CALC["calc.py"],
        "test_calc.py": (
            "from calc import add_one\n"
            "\n"
            "\n"
            "def test_add_one():\n"
            "    assert add_one(1) == 2\n"
        ),
    }
    _outer, project = parent_project(
        tmp_path, {"pytest.ini": CHECK_INI}, files
    )
    analysis = analyse_project(project)
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is True
    assert verdict.no_tests is True


# I4, disclosure of the governing source.


def test_the_report_names_a_parent_source(tmp_path):
    outer, project = parent_project(
        tmp_path, {"pytest.ini": CHECK_INI}, CALC
    )
    analysis = analyse_project(project)
    data = json.loads(to_json(analysis))
    assert data["collection_settings"] == {
        "python_functions": ["check_*"]
    }
    assert data["collection_settings_source"] == str(
        outer.resolve()
    )
    text = to_text(analysis)
    assert (
        f"collection settings source - {outer.resolve()}" in text
    )


def test_the_report_names_the_project_root_for_a_root_source(
    tmp_path,
):
    project = write_project(
        tmp_path / "rooted", {"pytest.ini": CHECK_INI, **CALC}
    )
    analysis = analyse_project(project)
    data = json.loads(to_json(analysis))
    assert data["collection_settings_source"] == "project root"
    assert "collection settings source - project root" in to_text(
        analysis
    )


def test_no_source_entry_appears_when_defaults_are_in_force(
    tmp_path,
):
    files = {
        "calc.py": CALC["calc.py"],
        "test_calc.py": (
            "from calc import add_one\n"
            "\n"
            "\n"
            "def test_add_one():\n"
            "    assert add_one(1) == 2\n"
            "    assert add_one(0) == 1\n"
        ),
    }
    project = write_project(tmp_path / "plain", files)
    analysis = analyse_project(project)
    data = json.loads(to_json(analysis))
    assert "collection_settings" not in data
    assert "collection_settings_source" not in data
    assert "collection settings" not in to_text(analysis)


# I5, path carrying patterns under a governing source in a parent.


def test_a_separator_pattern_from_a_parent_matches_project_relative(
    tmp_path,
):
    _outer, project = parent_project(
        tmp_path,
        {
            "pytest.ini": (
                "[pytest]\npython_files = deep/*_test.py\n"
            )
        },
        {
            "deep/check_test.py": (
                "def test_deep():\n    assert True\n"
            ),
            "top_test.py": "def test_top():\n    assert True\n",
        },
    )
    settings = load_collection_settings(project)
    assert settings.python_files == ("deep/*_test.py",)
    test_files, _sources = _discover(project, settings)
    assert [path.name for path in test_files] == ["check_test.py"]
    assert test_files[0].parent.name == "deep"
