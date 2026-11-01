"""Tests for the Round 8 review fixes in CONTRACT.md.

FIX-26 keeps a broken conftest from crashing the analysis,
FIX-27 bounds the conftest chain at the governing source
folder, and the equal tables shape pins the origin wording.
"""

from pathlib import Path

from cantfail.runner import analyse_project
from cantfail.static_scan import scan_source


def write_project(root, files):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _conftest(value):
    return (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        f"    made.fetch.return_value = {value}\n"
        "    return made\n"
    )


CONFTEST_42 = _conftest(42)
CONFTEST_9 = _conftest(9)

BROKEN_CONFTEST = "import pytest\n\ndef client(:\n"

MODULE_FIXTURE_42 = (
    "import pytest\n"
    "from unittest.mock import Mock\n"
    "\n"
    "@pytest.fixture\n"
    "def client():\n"
    "    made = Mock()\n"
    "    made.fetch.return_value = 42\n"
    "    return made\n"
    "\n"
)


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


# FIX-26, a broken supplier supplies nothing and clears nothing.


def test_a_broken_farther_conftest_does_not_hide_a_nearer_supply():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[BROKEN_CONFTEST, CONFTEST_42],
    )
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 2)
    ]
    assert "conftest fixture" in findings[0].detail


def test_a_broken_nearer_conftest_clears_nothing():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[CONFTEST_42, BROKEN_CONFTEST],
    )
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 2)
    ]
    assert "conftest fixture" in findings[0].detail


def test_an_analysis_with_a_broken_conftest_still_reports(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": BROKEN_CONFTEST,
            "test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert len(analysis.verdicts) == 1
    assert analysis.verdicts[0].status == "baseline_failed"


# FIX-27, the chain stops at the governing source folder.


def test_a_subfolder_inifile_keeps_the_root_supply_out(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": CONFTEST_42,
            "sub/pytest.ini": "[pytest]\n",
            "sub/test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert analysis.static_findings == []
    assert len(analysis.verdicts) == 1
    assert analysis.verdicts[0].status == "baseline_failed"


def test_a_conftest_below_the_inifile_floor_still_supplies(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": CONFTEST_42,
            "sub/pytest.ini": "[pytest]\n",
            "sub/conftest.py": CONFTEST_9,
            "sub/test_client.py": _fetch_test(9),
        },
    )
    analysis = analyse_project(project)
    assert [(item.kind, item.line) for item in analysis.static_findings] == [
        ("mock_return_value", 2)
    ]
    assert "conftest fixture" in analysis.static_findings[0].detail
    assert analysis.static_findings[0].detail.endswith(", 9")


# The origin wording on equal tables.


def test_equal_tables_keep_the_module_wording():
    source = MODULE_FIXTURE_42 + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[CONFTEST_42]
    )
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 11)
    ]
    assert "same file" in findings[0].detail
    assert "conftest fixture" not in findings[0].detail
    assert findings[0].detail.endswith(", 42")
