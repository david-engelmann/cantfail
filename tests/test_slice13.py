"""Tests for the slice 13 obligations in CONTRACT.md.

Slice 13 retires the loop and with and match limit N4
recorded after slice 12. The helper and fixture maps of a
module are built from one definition stream that now
descends through top level loops and with blocks and match
statements beside conditionals and tries, so a fixture
standing under one of those statements supplies and clears
exactly as one standing directly in the module body does,
while no iterable or manager or subject or guard is ever
evaluated and the selector and the shaped count keep their
own readings.

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


def _bare_fixture(indent):
    pad = " " * indent
    return (
        f"{pad}@pytest.fixture\n"
        f"{pad}def client():\n"
        f"{pad}    return Mock()\n"
    )


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


def _kinds_and_lines(findings):
    return [(item.kind, item.line) for item in findings]


def _wrapped(kind, fixture, indent=4):
    if kind == "for":
        return "for _ in range(1):\n" + fixture
    if kind == "while":
        return "while True:\n" + fixture
    if kind == "with":
        return "with manager:\n" + fixture
    if kind == "match":
        return "match 1:\n    case 1:\n" + fixture
    raise AssertionError(kind)


def _wrapped_return(kind, value):
    if kind == "match":
        return _wrapped(kind, _return_fixture(8, value))
    return _wrapped(kind, _return_fixture(4, value))


def _wrapped_bare(kind):
    if kind == "match":
        return _wrapped(kind, _bare_fixture(8))
    return _wrapped(kind, _bare_fixture(4))


# O1 and O2, the widened stream and the supply under it.


def test_a_fixture_under_a_for_loop_flags():
    source = HEAD + _wrapped_return("for", 42) + "\n" + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]
    assert "same file" in findings[0].detail
    assert findings[0].detail.endswith(", 42")
    other = source.replace("== 42", "== 43")
    assert scan_source(other, "test_client.py") == []


def test_a_fixture_under_a_while_loop_flags():
    source = HEAD + _wrapped_return("while", 42) + "\n" + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]


def test_a_fixture_inside_a_with_block_flags():
    source = HEAD + _wrapped_return("with", 42) + "\n" + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]


def test_a_fixture_inside_a_match_case_flags():
    source = HEAD + _wrapped_return("match", 42) + "\n" + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]


def test_a_conftest_for_loop_fixture_flags_down_the_chain():
    conftest = HEAD + _wrapped_return("for", 42)
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[conftest],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert "conftest fixture" in findings[0].detail


def test_a_conftest_while_loop_fixture_flags_down_the_chain():
    conftest = HEAD + _wrapped_return("while", 42)
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[conftest],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]


def test_a_conftest_with_block_fixture_flags_down_the_chain():
    conftest = HEAD + _wrapped_return("with", 42)
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[conftest],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]


def test_a_conftest_match_fixture_flags_down_the_chain():
    conftest = HEAD + _wrapped_return("match", 42)
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[conftest],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]


def test_a_module_loop_fixture_shadows_a_conftest_fixture():
    conftest = HEAD + _return_fixture(0, 7)
    source = HEAD + _wrapped_return("for", 42) + "\n" + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[conftest]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]
    assert "same file" in findings[0].detail
    shadowed = source.replace("== 42", "== 7")
    assert (
        scan_source(shadowed, "test_client.py", supply_sources=[conftest])
        == []
    )


def test_a_module_with_fixture_shadows_a_conftest_fixture():
    conftest = HEAD + _return_fixture(0, 7)
    source = HEAD + _wrapped_return("with", 42) + "\n" + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[conftest]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]
    shadowed = source.replace("== 42", "== 7")
    assert (
        scan_source(shadowed, "test_client.py", supply_sources=[conftest])
        == []
    )


def test_a_module_match_fixture_shadows_a_conftest_fixture():
    conftest = HEAD + _return_fixture(0, 7)
    source = HEAD + _wrapped_return("match", 42) + "\n" + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[conftest]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]
    shadowed = source.replace("== 42", "== 7")
    assert (
        scan_source(shadowed, "test_client.py", supply_sources=[conftest])
        == []
    )


def test_a_nearer_loop_fixture_clears_a_farther_table():
    farther = HEAD + _return_fixture(0, 42)
    nearer = HEAD + _wrapped_bare("for")
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[farther, nearer],
    )
    assert findings == []


def test_a_nearer_with_fixture_clears_a_farther_table():
    farther = HEAD + _return_fixture(0, 42)
    nearer = HEAD + _wrapped_bare("with")
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[farther, nearer],
    )
    assert findings == []


def test_a_nearer_match_fixture_clears_a_farther_table():
    farther = HEAD + _return_fixture(0, 42)
    nearer = HEAD + _wrapped_bare("match")
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[farther, nearer],
    )
    assert findings == []


def test_a_module_loop_bare_fixture_clears_a_conftest_table():
    conftest = HEAD + _return_fixture(0, 42)
    source = HEAD + _wrapped_bare("for") + "\n" + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[conftest]
    )
    assert findings == []


def test_a_module_match_bare_fixture_clears_a_conftest_table():
    conftest = HEAD + _return_fixture(0, 42)
    source = HEAD + _wrapped_bare("match") + "\n" + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[conftest]
    )
    assert findings == []


def test_a_loop_redefinition_clears_the_helper_entry():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
        "\n"
        "for _ in range(1):\n"
        "    def make_client():\n"
        "        return Mock()\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_client()\n"
        "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_with_redefinition_clears_the_helper_entry():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
        "\n"
        "with manager:\n"
        "    def make_client():\n"
        "        return Mock()\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_client()\n"
        "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_two_match_cases_read_the_definition_standing_later():
    source = (
        HEAD
        + "match 1:\n"
        + "    case 1:\n"
        + _return_fixture(8, 42)
        + "    case 2:\n"
        + _return_fixture(8, 7)
        + "\n"
        + _fetch_test(7)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 19)]
    assert findings[0].detail.endswith(", 7")
    earlier = source.replace("== 7", "== 42")
    assert scan_source(earlier, "test_client.py") == []


def test_a_fixture_in_a_for_else_list_flags():
    source = (
        HEAD
        + "for _ in range(1):\n    pass\nelse:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_fixture_in_a_while_else_list_flags():
    source = (
        HEAD
        + "while False:\n    pass\nelse:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_fixture_under_a_match_guard_flags():
    source = (
        HEAD
        + "match 1:\n"
        + "    case 1 if False:\n"
        + _return_fixture(8, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]


def test_a_conditional_inside_a_loop_flags():
    source = (
        HEAD
        + "for _ in range(1):\n    if True:\n"
        + _return_fixture(8, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]


def test_a_loop_inside_a_conditional_flags():
    source = (
        HEAD
        + "if True:\n    for _ in range(1):\n"
        + _return_fixture(8, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]


def test_a_with_block_inside_a_try_flags():
    source = (
        HEAD
        + "try:\n    with manager:\n"
        + _return_fixture(8, 42)
        + "except Exception:\n    pass\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]


def test_a_try_inside_a_with_block_flags():
    source = (
        HEAD
        + "with manager:\n    try:\n"
        + _return_fixture(8, 42)
        + "    except Exception:\n        pass\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]


def test_a_loop_inside_a_match_case_flags():
    source = (
        HEAD
        + "match 1:\n    case 1:\n        for _ in range(1):\n"
        + _return_fixture(12, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_match_inside_a_loop_flags():
    source = (
        HEAD
        + "for _ in range(1):\n    match 1:\n        case 1:\n"
        + _return_fixture(12, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_yield_fixture_under_a_loop_flags_its_setup_literal():
    source = (
        HEAD
        + "for _ in range(1):\n"
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
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]
    teardown = source.replace("== 42", "== 7")
    assert scan_source(teardown, "test_client.py") == []


def test_a_delegating_fixture_under_a_match_flags():
    source = (
        HEAD
        + "def _provision():\n"
        + "    made = Mock()\n"
        + "    made.fetch.return_value = 42\n"
        + "    yield made\n"
        + "\n"
        + "match 1:\n"
        + "    case 1:\n"
        + "        @pytest.fixture\n"
        + "        def client():\n"
        + "            yield from _provision()\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 16)]


def test_a_fixture_delegating_to_a_with_block_delegate_flags():
    source = (
        HEAD
        + "with manager:\n"
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
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]


# O1 at the scan gate, the effective definition reading of J1.


def test_a_loop_fixture_redefinition_withholds_findings():
    source = (
        HEAD
        + "def test_client():\n"
        + "    assert True\n"
        + "\n"
        + "for _ in range(1):\n"
        + "    @pytest.fixture\n"
        + "    def test_client():\n"
        + "        return Mock()\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_match_plain_redefinition_gives_the_findings_back():
    source = (
        HEAD
        + "@pytest.fixture\n"
        + "def test_client():\n"
        + "    assert True\n"
        + "\n"
        + "match 1:\n"
        + "    case 1:\n"
        + "        def test_client():\n"
        + "            return Mock()\n"
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("constant_assert", 6)]


# O3 and O4, the composition boundaries and the parting from a run.


def test_an_assertion_inside_a_match_definition_earns_no_finding():
    source = (
        HEAD
        + "match 1:\n"
        + "    case 1:\n"
        + "        def test_thing():\n"
        + "            assert True\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_test_function_under_a_loop_is_not_selected():
    source = (
        "for _ in range(1):\n"
        "    def test_other():\n"
        "        pass\n"
        "\n"
        "def test_plain():\n"
        "    pass\n"
    )
    assert selectable_test_items(source) == ["test_plain"]


def test_a_fixture_under_a_never_running_loop_is_read_all_the_same():
    source = (
        HEAD
        + "while False:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]


def test_a_fixture_under_a_raising_with_manager_is_read_all_the_same():
    source = (
        HEAD
        + "with BadManager():\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]


def test_a_loop_else_fixture_is_read_behind_a_break():
    source = (
        HEAD
        + "for _ in range(1):\n    break\nelse:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_fixture_in_a_class_body_under_a_loop_is_not_module_supply():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + "    class Holder:\n"
        + "        @pytest.fixture\n"
        + "        def client(self):\n"
        + "            made = Mock()\n"
        + "            made.fetch.return_value = 42\n"
        + "            return made\n"
        + "\n"
        + _fetch_test(42)
    )
    assert scan_source(source, "test_client.py") == []


def test_a_fixture_inside_a_function_under_a_loop_is_not_read():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + "    def outer():\n"
        + "        @pytest.fixture\n"
        + "        def client():\n"
        + "            made = Mock()\n"
        + "            made.fetch.return_value = 42\n"
        + "            return made\n"
        + "\n"
        + _fetch_test(42)
    )
    assert scan_source(source, "test_client.py") == []


# O2 at the level of a whole analysis, through the runner chain.


def test_a_project_with_a_conftest_match_fixture_flags(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": HEAD + _wrapped_return("match", 42),
            "test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert [item.kind for item in analysis.static_findings] == [
        "mock_return_value"
    ]
