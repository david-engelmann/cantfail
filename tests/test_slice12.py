"""Tests for the slice 12 obligations in CONTRACT.md.

Slice 12 retires the conditional half of the limit FIX-28
recorded in K5. The helper and fixture maps of a module are
built from one definition stream that descends through top
level conditional and try statements in source order, so a
fixture standing under a top level conditional supplies
and clears exactly as one standing directly in the module
body does, while no condition is ever evaluated and the
selector and the shaped count keep their own readings.

Every fixture here is synthetic and written for this test
file. The readings were arbitrated against the installed
pytest 9.1.1 before the obligations were written, and the
probe projects behind them are the shapes the contract
preamble records.
"""

from pathlib import Path

from cantfail.runner import analyse_project
from cantfail.static_scan import scan_source, selectable_test_items


def write_project(root, files):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


HEAD = "import pytest\nfrom unittest.mock import Mock\n\n"


def _return_fixture(indent, value):
    pad = " " * indent
    return (
        f"{pad}@pytest.fixture\n"
        f"{pad}def client():\n"
        f"{pad}    made = Mock()\n"
        f"{pad}    made.fetch.return_value = {value}\n"
        f"{pad}    return made\n"
    )


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


def _kinds_and_lines(findings):
    return [(item.kind, item.line) for item in findings]


# N1 and N2, the stream and the supply under it.


def test_a_fixture_under_a_top_level_conditional_flags():
    source = (
        HEAD
        + "READY = True\n\nif READY:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]
    assert "same file" in findings[0].detail
    assert findings[0].detail.endswith(", 42")
    other = source.replace("== 42", "== 43")
    assert scan_source(other, "test_client.py") == []


def test_a_fixture_in_the_else_branch_flags():
    source = (
        HEAD
        + "READY = False\n\nif READY:\n    pass\nelse:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 16)]


def test_both_branches_read_the_definition_standing_later():
    source = (
        HEAD
        + "READY = True\n\nif READY:\n"
        + _return_fixture(4, 42)
        + "else:\n"
        + _return_fixture(4, 7)
        + "\n"
        + _fetch_test(7)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 20)]
    assert findings[0].detail.endswith(", 7")
    earlier = source.replace("== 7", "== 42")
    assert scan_source(earlier, "test_client.py") == []


def test_a_nested_conditional_fixture_flags():
    source = (
        HEAD
        + "OUTER = True\nINNER = True\n\nif OUTER:\n    if INNER:\n"
        + _return_fixture(8, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 16)]


def test_a_fixture_standing_in_a_try_body_flags():
    source = (
        HEAD
        + "try:\n"
        + _return_fixture(4, 42)
        + "except Exception:\n    pass\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_fixture_standing_in_a_handler_body_flags():
    source = (
        HEAD
        + "try:\n    raise RuntimeError('boom')\nexcept RuntimeError:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_fixture_standing_in_a_try_else_flags():
    source = (
        HEAD
        + "try:\n    pass\nexcept Exception:\n    pass\nelse:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 16)]


def test_a_fixture_standing_in_a_finally_block_flags():
    source = (
        HEAD
        + "try:\n    pass\nfinally:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_conditional_standing_inside_a_try_flags():
    source = (
        HEAD
        + "READY = True\n\ntry:\n    if READY:\n"
        + _return_fixture(8, 42)
        + "except Exception:\n    pass\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 17)]


def test_a_conftest_conditional_fixture_flags_down_the_chain():
    conftest = (
        HEAD
        + "READY = True\n\nif READY:\n"
        + _return_fixture(4, 42)
    )
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[conftest],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert "conftest fixture" in findings[0].detail
    assert findings[0].detail.endswith(", 42")


def test_a_module_conditional_fixture_shadows_a_conftest_fixture():
    conftest = HEAD + _return_fixture(0, 7)
    source = (
        HEAD
        + "READY = True\n\nif READY:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(
        source, "test_client.py", supply_sources=[conftest]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]
    assert "same file" in findings[0].detail
    shadowed = source.replace("== 42", "== 7")
    assert (
        scan_source(shadowed, "test_client.py", supply_sources=[conftest])
        == []
    )


def test_a_nearer_conditional_fixture_clears_a_farther_table():
    farther = HEAD + _return_fixture(0, 42)
    nearer = (
        HEAD
        + "READY = True\n\nif READY:\n"
        + "    @pytest.fixture\n"
        + "    def client():\n"
        + "        return Mock()\n"
    )
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[farther, nearer],
    )
    assert findings == []


def test_a_module_conditional_bare_fixture_clears_a_conftest_table():
    conftest = HEAD + _return_fixture(0, 42)
    source = (
        HEAD
        + "READY = True\n\nif READY:\n"
        + "    @pytest.fixture\n"
        + "    def client():\n"
        + "        return Mock()\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(
        source, "test_client.py", supply_sources=[conftest]
    )
    assert findings == []


def test_a_conditional_redefinition_clears_the_helper_entry():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
        "\n"
        "READY = True\n"
        "\n"
        "if READY:\n"
        "    def make_client():\n"
        "        return Mock()\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_client()\n"
        "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_later_unconditional_definition_overrides_a_conditional_one():
    source = (
        HEAD
        + "READY = True\n\nif READY:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _return_fixture(0, 7)
        + "\n"
        + _fetch_test(7)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 20)]
    earlier = source.replace("== 7", "== 42")
    assert scan_source(earlier, "test_client.py") == []


def test_a_yield_fixture_under_a_conditional_flags_its_setup_literal():
    source = (
        HEAD
        + "READY = True\n\nif READY:\n"
        + "    @pytest.fixture\n"
        + "    def client():\n"
        + "        made = Mock()\n"
        + "        made.fetch.return_value = 42\n"
        + "        yield made\n"
        + "        made.fetch.return_value = 7\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]
    teardown = source.replace("== 42", "== 7")
    assert scan_source(teardown, "test_client.py") == []


def test_a_delegating_fixture_under_a_conditional_flags():
    source = (
        HEAD
        + "def _provision():\n"
        + "    made = Mock()\n"
        + "    made.fetch.return_value = 42\n"
        + "    yield made\n"
        + "\n"
        + "READY = True\n"
        + "\n"
        + "if READY:\n"
        + "    @pytest.fixture\n"
        + "    def client():\n"
        + "        yield from _provision()\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 17)]


def test_a_fixture_delegating_to_a_conditional_delegate_flags():
    source = (
        HEAD
        + "READY = True\n"
        + "\n"
        + "if READY:\n"
        + "    def _provision():\n"
        + "        made = Mock()\n"
        + "        made.fetch.return_value = 42\n"
        + "        yield made\n"
        + "\n"
        + "@pytest.fixture\n"
        + "def client():\n"
        + "    yield from _provision()\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 17)]


# N1 at the scan gate, the effective definition reading of J1.


def test_a_conditional_fixture_redefinition_withholds_findings():
    source = (
        HEAD
        + "def test_client():\n"
        + "    assert True\n"
        + "\n"
        + "READY = True\n"
        + "\n"
        + "if READY:\n"
        + "    @pytest.fixture\n"
        + "    def test_client():\n"
        + "        return Mock()\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_conditional_plain_redefinition_gives_the_findings_back():
    source = (
        HEAD
        + "@pytest.fixture\n"
        + "def test_client():\n"
        + "    assert True\n"
        + "\n"
        + "READY = True\n"
        + "\n"
        + "if READY:\n"
        + "    def test_client():\n"
        + "        return Mock()\n"
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("constant_assert", 6)]


# N3, the composition boundaries.


def test_an_assertion_inside_a_conditional_definition_earns_no_finding():
    source = (
        HEAD
        + "READY = True\n"
        + "\n"
        + "if READY:\n"
        + "    def test_thing():\n"
        + "        assert True\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_test_function_under_a_conditional_is_not_selected():
    source = (
        "READY = True\n"
        "\n"
        "if READY:\n"
        "    def test_other():\n"
        "        pass\n"
        "\n"
        "def test_plain():\n"
        "    pass\n"
    )
    assert selectable_test_items(source) == ["test_plain"]


# N4, the limits that stay.


def test_a_fixture_under_a_false_condition_is_read_all_the_same():
    source = (
        HEAD
        + "READY = False\n\nif READY:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_fixture_inside_a_top_level_loop_is_not_read():
    source = (
        HEAD
        + "while True:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    assert scan_source(source, "test_client.py") == []


def test_a_fixture_inside_a_top_level_with_block_is_not_read():
    source = (
        HEAD
        + "with manager:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    assert scan_source(source, "test_client.py") == []


def test_a_fixture_in_a_class_body_is_not_module_supply():
    source = (
        HEAD
        + "class Holder:\n"
        + "    @pytest.fixture\n"
        + "    def client(self):\n"
        + "        made = Mock()\n"
        + "        made.fetch.return_value = 42\n"
        + "        return made\n"
        + "\n"
        + _fetch_test(42)
    )
    assert scan_source(source, "test_client.py") == []


# N2 at the level of a whole analysis, through the runner chain.


def test_a_project_with_a_conftest_conditional_fixture_flags(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": (
                HEAD
                + "READY = True\n\nif READY:\n"
                + _return_fixture(4, 42)
            ),
            "test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert [item.kind for item in analysis.static_findings] == [
        "mock_return_value"
    ]
