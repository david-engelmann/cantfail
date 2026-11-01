"""Tests for the slice 9 obligations in CONTRACT.md.

Slice 9 widens the fixture form of D5 beyond the file that
holds the test. The fixture definitions of the project
conftest files on the chain for a test file join the fixture
table the scan reads, under the precedence K2 states, while a
conftest itself is never a target under K3 and the verdict
path, which has always resolved the supply inside its runs, is
pinned under K4.

Every fixture here is synthetic and written for this test file.
The readings were arbitrated against the installed pytest
9.1.1 before the obligations were written, and the probe
projects behind the precedence tests are the shapes the
contract preamble records.
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

CONFTEST_EMPTY = (
    "import pytest\n"
    "from unittest.mock import Mock\n"
    "\n"
    "@pytest.fixture\n"
    "def client():\n"
    "    return Mock()\n"
)

CONFTEST_PLAIN = (
    "from unittest.mock import Mock\n"
    "\n"
    "def client():\n"
    "    made = Mock()\n"
    "    made.fetch.return_value = 9\n"
    "    return made\n"
)

CONFTEST_DUPLICATE = _conftest(42) + (
    "\n"
    "@pytest.fixture\n"
    "def client():\n"
    "    made = Mock()\n"
    "    made.fetch.return_value = 9\n"
    "    return made\n"
)

CONFTEST_HELPER = (
    "from unittest.mock import Mock\n"
    "\n"
    "def make_client():\n"
    "    made = Mock()\n"
    "    made.fetch.return_value = 42\n"
    "    return made\n"
)

MODULE_FIXTURE_7 = (
    "import pytest\n"
    "from unittest.mock import Mock\n"
    "\n"
    "@pytest.fixture\n"
    "def client():\n"
    "    made = Mock()\n"
    "    made.fetch.return_value = 7\n"
    "    return made\n"
    "\n"
)


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


def _kinds_and_lines(findings):
    return [(item.kind, item.line) for item in findings]


# K1, the supply reaching the scan.


def test_a_conftest_supplied_fixture_flags_the_fixture_form():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[CONFTEST_42],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert "conftest fixture" in findings[0].detail
    assert findings[0].detail.endswith(", 42")


def test_the_same_test_without_the_supply_earns_no_finding():
    assert scan_source(_fetch_test(42), "test_client.py") == []


def test_a_conftest_fixture_asserted_against_another_literal_stands():
    findings = scan_source(
        _fetch_test(43),
        "test_client.py",
        supply_sources=[CONFTEST_42],
    )
    assert findings == []


def test_the_supply_flags_an_assertion_inside_a_nested_definition():
    source = (
        "def test_fetch(client):\n"
        "    def check():\n"
        "        assert client.fetch() == 42\n"
        "    check()\n"
    )
    findings = scan_source(
        source, "test_client.py", supply_sources=[CONFTEST_42]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 3)]


def test_a_kwonly_fixture_argument_draws_on_the_supply():
    source = (
        "def test_fetch(*, client):\n"
        "    assert client.fetch() == 42\n"
    )
    findings = scan_source(
        source, "test_client.py", supply_sources=[CONFTEST_42]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]


def test_the_supply_flags_a_method_that_consumes_the_fixture():
    source = (
        "class TestFetch:\n"
        "    def test_fetch(self, client):\n"
        "        assert client.fetch() == 42\n"
    )
    findings = scan_source(
        source, "test_client.py", supply_sources=[CONFTEST_42]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 3)]


def test_a_conftest_definition_is_never_read_as_a_helper():
    source = (
        "def test_fetch():\n"
        "    client = make_client()\n"
        "    assert client.fetch() == 42\n"
    )
    findings = scan_source(
        source, "test_client.py", supply_sources=[CONFTEST_HELPER]
    )
    assert findings == []


def test_an_analysis_flags_a_test_fed_by_the_project_conftest(
    tmp_path,
):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": CONFTEST_42,
            "test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert _kinds_and_lines(analysis.static_findings) == [
        ("mock_return_value", 2)
    ]
    assert analysis.static_findings[0].path == "test_client.py"


def test_a_parent_folder_conftest_supplies_a_nested_test_file(
    tmp_path,
):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": CONFTEST_42,
            "sub/test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert _kinds_and_lines(analysis.static_findings) == [
        ("mock_return_value", 2)
    ]
    assert analysis.static_findings[0].path == "sub/test_client.py"


# K2, precedence among the suppliers.


def test_a_module_fixture_shadows_the_conftest_supply():
    source = MODULE_FIXTURE_7 + _fetch_test(7)
    findings = scan_source(
        source, "test_client.py", supply_sources=[CONFTEST_42]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 11)]
    assert "same file" in findings[0].detail
    assert findings[0].detail.endswith(", 7")


def test_the_shadowed_conftest_value_earns_no_finding():
    source = MODULE_FIXTURE_7 + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[CONFTEST_42]
    )
    assert findings == []


def test_a_nearer_conftest_shadows_a_farther_one():
    findings = scan_source(
        _fetch_test(9),
        "test_client.py",
        supply_sources=[CONFTEST_42, CONFTEST_9],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert findings[0].detail.endswith(", 9")


def test_the_farther_value_earns_no_finding_behind_a_nearer_one():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[CONFTEST_42, CONFTEST_9],
    )
    assert findings == []


def test_a_nearer_fixture_that_configures_nothing_clears_the_supply():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[CONFTEST_42, CONFTEST_EMPTY],
    )
    assert findings == []


def test_a_plain_definition_in_a_nearer_conftest_leaves_the_supply():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[CONFTEST_42, CONFTEST_PLAIN],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert findings[0].detail.endswith(", 42")


def test_a_plain_definition_in_the_module_leaves_the_supply():
    source = CONFTEST_PLAIN + "\n" + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[CONFTEST_42]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 9)]
    assert "conftest fixture" in findings[0].detail


def test_the_last_definition_inside_one_conftest_decides():
    supplied = scan_source(
        _fetch_test(9),
        "test_client.py",
        supply_sources=[CONFTEST_DUPLICATE],
    )
    assert _kinds_and_lines(supplied) == [("mock_return_value", 2)]
    assert supplied[0].detail.endswith(", 9")
    shadowed = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[CONFTEST_DUPLICATE],
    )
    assert shadowed == []


def test_a_nearer_conftest_in_the_folder_shadows_the_root_one(
    tmp_path,
):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": CONFTEST_42,
            "sub/conftest.py": CONFTEST_9,
            "sub/test_client.py": _fetch_test(9),
        },
    )
    analysis = analyse_project(project)
    assert _kinds_and_lines(analysis.static_findings) == [
        ("mock_return_value", 2)
    ]
    assert analysis.static_findings[0].detail.endswith(", 9")


# K3, the conftest never being a target.


def test_a_conftest_earns_no_verdict_and_no_finding(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": (
                "import pytest\n"
                "\n"
                "@pytest.fixture\n"
                "def test_shaped():\n"
                "    return 1\n"
                "\n"
                "def test_plain():\n"
                "    assert True\n"
            ),
            "test_plain.py": (
                "def test_real():\n"
                "    assert len('ab') == 2\n"
            ),
        },
    )
    analysis = analyse_project(project)
    assert [item.path for item in analysis.verdicts] == [
        "test_plain.py"
    ]
    assert analysis.verdicts[0].test_functions == ["test_real"]
    assert analysis.static_findings == []


def test_a_refused_conftest_fails_the_verdict_like_the_run(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": (
                "import pytest\n"
                "\n"
                "@pytest.fixture\n"
                "class Helper:\n"
                "    pass\n"
            ),
            "test_plain.py": (
                "def test_real():\n"
                "    assert len('ab') == 2\n"
            ),
        },
    )
    analysis = analyse_project(project)
    assert len(analysis.verdicts) == 1
    verdict = analysis.verdicts[0]
    assert verdict.status == "baseline_failed"
    assert verdict.no_tests is False


# K4, the verdict path pinned.


def test_a_conftest_fed_test_is_judged_on_the_panel(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": CONFTEST_42,
            "svc.py": "def fetch():\n    return 42\n",
            "test_svc.py": (
                "from svc import fetch\n"
                "\n"
                "\n"
                "def test_fetch_value(client):\n"
                "    assert fetch() == 42\n"
                "    assert client.fetch() == 42\n"
            ),
        },
    )
    analysis = analyse_project(project)
    assert len(analysis.verdicts) == 1
    verdict = analysis.verdicts[0]
    assert verdict.test_functions == ["test_fetch_value"]
    assert verdict.functions[0].baseline_ok is True
    assert verdict.functions[0].status == "can_fail"
    assert verdict.status == "can_fail"
    assert _kinds_and_lines(analysis.static_findings) == [
        ("mock_return_value", 6)
    ]


def test_the_testcase_carve_out_stands_under_conftest_supply(
    tmp_path,
):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": CONFTEST_42,
            "test_widget.py": (
                "import unittest\n"
                "\n"
                "import pytest\n"
                "\n"
                "\n"
                "def test_uses_client(client):\n"
                "    assert client.fetch() == 42\n"
                "\n"
                "\n"
                "class TestWidget(unittest.TestCase):\n"
                "    @pytest.fixture\n"
                "    def test_thing(self):\n"
                "        return 1\n"
                "\n"
                "    def test_plain(self):\n"
                "        assert len('ab') == 2\n"
            ),
        },
    )
    analysis = analyse_project(project)
    assert len(analysis.verdicts) == 1
    verdict = analysis.verdicts[0]
    assert "TestWidget::test_thing" in verdict.test_functions
    by_name = {item.name: item for item in verdict.functions}
    assert by_name["TestWidget::test_thing"].status == (
        "baseline_failed"
    )
    assert by_name["test_uses_client"].baseline_ok is True


# K5, the limits that stay.


def test_a_conftest_in_a_sibling_folder_supplies_nothing(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "other/conftest.py": CONFTEST_42,
            "test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert analysis.static_findings == []


def test_a_conftest_above_the_project_root_supplies_nothing(
    tmp_path,
):
    outer = write_project(
        tmp_path / "outer", {"conftest.py": CONFTEST_42}
    )
    project = write_project(
        outer / "inner", {"test_client.py": _fetch_test(42)}
    )
    analysis = analyse_project(project)
    assert analysis.static_findings == []


def test_a_fixture_registered_under_another_name_is_not_read(
    tmp_path,
):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": (
                "import pytest\n"
                "from unittest.mock import Mock\n"
                "\n"
                "@pytest.fixture(name='alias')\n"
                "def client():\n"
                "    made = Mock()\n"
                "    made.fetch.return_value = 42\n"
                "    return made\n"
            ),
            "test_client.py": (
                "def test_fetch(alias):\n"
                "    assert alias.fetch() == 42\n"
            ),
        },
    )
    analysis = analyse_project(project)
    assert analysis.static_findings == []
