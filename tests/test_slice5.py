"""Tests for the slice 5 obligations in CONTRACT.md.

Slice 5 makes the static scan follow the collection naming
settings. A finding is reported only for an assertion inside a
test function as the python_functions setting in force names
test functions, with replacement semantics. Every fixture here
is synthetic and written for this test file.
"""

import json

from cantfail.report import to_json
from cantfail.runner import analyse_project
from cantfail.settings import CollectionSettings
from cantfail.static_scan import scan_file, scan_source
from factories import DECORATIVE, write_project

CHECK_SETTINGS = CollectionSettings(python_functions=("check_*",))

MOCK_IN_TWO_NAMES = (
    "from unittest.mock import Mock\n"
    "\n"
    "def check_fetch():\n"
    "    client = Mock()\n"
    "    client.fetch.return_value = 42\n"
    "    result = client.fetch()\n"
    "    assert result == 42\n"
    "\n"
    "\n"
    "def test_fetch():\n"
    "    client = Mock()\n"
    "    client.fetch.return_value = 42\n"
    "    result = client.fetch()\n"
    "    assert result == 42\n"
)


# G1, the scan entry points take the settings.


def test_scan_file_takes_the_settings(tmp_path):
    target = tmp_path / "test_names.py"
    target.write_text(MOCK_IN_TWO_NAMES, encoding="utf-8")
    custom = scan_file(target, "test_names.py", CHECK_SETTINGS)
    assert [(item.kind, item.line) for item in custom] == [
        ("mock_return_value", 7)
    ]
    default = scan_file(target, "test_names.py")
    assert [(item.kind, item.line) for item in default] == [
        ("mock_return_value", 14)
    ]


# G2, what counts as a test function for the scan.


def test_a_custom_prefix_flags_the_custom_named_mock_function():
    findings = scan_source(
        MOCK_IN_TWO_NAMES, "test_names.py", CHECK_SETTINGS
    )
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 7)
    ]


def test_the_default_reading_flags_the_test_named_mock_function():
    findings = scan_source(MOCK_IN_TWO_NAMES, "test_names.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 14)
    ]


def test_the_helper_form_follows_the_function_setting():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_client():\n"
        "    svc = Mock()\n"
        "    svc.fetch.return_value = 42\n"
        "    return svc\n"
        "\n"
        "\n"
        "def check_fetch():\n"
        "    client = make_client()\n"
        "    assert client.fetch() == 42\n"
        "\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_client()\n"
        "    assert client.fetch() == 42\n"
    )
    custom = scan_source(source, "test_helper.py", CHECK_SETTINGS)
    assert [(item.kind, item.line) for item in custom] == [
        ("mock_return_value", 11)
    ]
    assert "helper or fixture" in custom[0].detail
    default = scan_source(source, "test_helper.py")
    assert [(item.kind, item.line) for item in default] == [
        ("mock_return_value", 16)
    ]


def test_the_other_patterns_follow_the_function_setting():
    source = (
        "def check_shapes():\n"
        "    total = 3\n"
        "    assert total == total\n"
        "    assert True\n"
        "\n"
        "\n"
        "def test_shapes():\n"
        "    assert True\n"
    )
    custom = scan_source(source, "test_shapes.py", CHECK_SETTINGS)
    assert [(item.kind, item.line) for item in custom] == [
        ("self_comparison", 3),
        ("constant_assert", 4),
    ]
    default = scan_source(source, "test_shapes.py")
    assert [(item.kind, item.line) for item in default] == [
        ("constant_assert", 8)
    ]


def test_a_nested_definition_belongs_to_its_outer_definition():
    inside_helper = (
        "def make_outer():\n"
        "    def test_inner():\n"
        "        assert True\n"
    )
    assert scan_source(inside_helper, "test_nested.py") == []
    inside_test = (
        "def test_outer():\n"
        "    def inner():\n"
        "        assert True\n"
    )
    findings = scan_source(inside_test, "test_nested.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("constant_assert", 3)
    ]


def test_a_module_level_assertion_earns_no_finding():
    assert scan_source("assert True\n", "test_level.py") == []
    assert (
        scan_source("assert True\n", "test_level.py", CHECK_SETTINGS)
        == []
    )


def test_a_shape_inside_a_helper_earns_no_finding_at_defaults():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def compute_check():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 42\n"
        "\n"
        "\n"
        "def test_fetch():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 42\n"
    )
    findings = scan_source(source, "test_names.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 14)
    ]


# G3, the scan takes no class name rule.


def test_a_method_earns_findings_by_its_method_name_alone():
    source = (
        "class Plain:\n"
        "    def test_m(self):\n"
        "        assert True\n"
        "\n"
        "\n"
        "class Other:\n"
        "    def check_m(self):\n"
        "        assert True\n"
    )
    default = scan_source(source, "test_methods.py")
    assert [(item.kind, item.line) for item in default] == [
        ("constant_assert", 3)
    ]
    custom = scan_source(source, "test_methods.py", CHECK_SETTINGS)
    assert [(item.kind, item.line) for item in custom] == [
        ("constant_assert", 8)
    ]
    class_setting_only = CollectionSettings(
        python_classes=("Other",)
    )
    by_class = scan_source(
        source, "test_methods.py", class_setting_only
    )
    assert [(item.kind, item.line) for item in by_class] == [
        ("constant_assert", 3)
    ]


# The headline proofs, run end to end through the analysis.

CUSTOM_PREFIX_PROJECT = {
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


def test_custom_prefix_project_is_judged_and_flagged(tmp_path):
    project = write_project(
        tmp_path / "customscan", CUSTOM_PREFIX_PROJECT
    )
    analysis = analyse_project(project, timeout=60)
    (verdict,) = analysis.verdicts
    by_name = {item.name: item.status for item in verdict.functions}
    assert by_name == {
        "check_adds": "can_fail",
        "check_fetch_returns_what_it_was_told": (
            "decorative_candidate"
        ),
    }
    assert [
        (item.kind, item.path, item.line)
        for item in analysis.static_findings
    ] == [("mock_return_value", "test_calc.py", 14)]
    assert analysis.collection_settings == {
        "python_functions": ["check_*"]
    }
    data = json.loads(to_json(analysis))
    assert data["schema"] == "cantfail-report/3"
    assert data["static_findings"][0]["kind"] == "mock_return_value"


def test_the_same_project_without_settings_falls_back(tmp_path):
    files = {
        name: content
        for name, content in CUSTOM_PREFIX_PROJECT.items()
        if name != "pyproject.toml"
    }
    project = write_project(tmp_path / "defaultscan", files)
    analysis = analyse_project(project, timeout=60)
    (verdict,) = analysis.verdicts
    assert verdict.whole_file is True
    assert verdict.no_tests is True
    assert verdict.status == "no_applicable_mutants"
    assert analysis.static_findings == []
    assert analysis.collection_settings == {}


def test_a_deselected_function_earns_no_item_and_no_finding(tmp_path):
    files = dict(CUSTOM_PREFIX_PROJECT)
    files["test_calc.py"] = (
        "from unittest.mock import Mock\n"
        "\n"
        "from calc import add_one\n"
        "\n"
        "\n"
        "def check_adds():\n"
        "    assert add_one(1) == 2\n"
        "\n"
        "\n"
        "def test_fetch_returns_what_it_was_told():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 42\n"
    )
    project = write_project(tmp_path / "deselected", files)
    analysis = analyse_project(project, timeout=60)
    (verdict,) = analysis.verdicts
    assert verdict.test_functions == ["check_adds"]
    assert [item.name for item in verdict.functions] == ["check_adds"]
    assert verdict.partial_selection is False
    assert analysis.static_findings == []


def test_a_defaults_project_keeps_the_pre_slice_findings(tmp_path):
    project = write_project(tmp_path / "decorative", DECORATIVE)
    analysis = analyse_project(project, timeout=60)
    assert [
        (item.kind, item.path, item.line)
        for item in analysis.static_findings
    ] == [("mock_return_value", "test_greeter.py", 8)]
    (verdict,) = analysis.verdicts
    assert verdict.status == "decorative_candidate"
