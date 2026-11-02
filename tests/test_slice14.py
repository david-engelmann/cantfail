"""Tests for the slice 14 obligations in CONTRACT.md.

Slice 14 retires the reach limit O3 recorded for the fixture
decorated class reading of FIX-23. The reading now follows
every statement list the one definition stream descends
through and crosses into the class bodies standing in them,
so a fixture decorated class standing under a conditional or
a try or a loop or a with block or a match statement withholds
the module items exactly as a direct one does, and a supplier
holding such a class is inert in the conftest fold.

Every fixture here is synthetic and written for this test
file. The readings were arbitrated against the installed
pytest 9.1.1 before the obligations were written, and the
probe projects behind them are the shapes the contract
preamble records.
"""

from cantfail.static_scan import (
    has_unselected_test_shapes,
    scan_source,
    selectable_test_items,
)

HEAD = "import pytest\nfrom unittest.mock import Mock\n\n"

PLAIN_TEST = "def test_real():\n    assert True\n"


def _fixture_class(indent):
    pad = " " * indent
    return (
        f"{pad}@pytest.fixture\n"
        f"{pad}class Holder:\n"
        f"{pad}    pass\n"
    )


def _poisoned(source):
    assert selectable_test_items(source) == []
    assert has_unselected_test_shapes(source, []) is False


def _clean(source):
    assert selectable_test_items(source) == ["test_real"]
    assert has_unselected_test_shapes(source, ["test_real"]) is False


# P1 and P2, the widened reach and the withholding.


def test_a_fixture_class_under_a_conditional_poisons_the_module():
    source = HEAD + "if True:\n" + _fixture_class(4) + "\n" + PLAIN_TEST
    _poisoned(source)


def test_a_fixture_class_in_a_taken_else_branch_poisons_the_module():
    source = (
        HEAD
        + "if False:\n    pass\nelse:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_try_body_poisons_the_module():
    source = (
        HEAD
        + "try:\n"
        + _fixture_class(4)
        + "except ValueError:\n    pass\n"
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_handler_body_poisons_the_module():
    source = (
        HEAD
        + "try:\n    raise ValueError\n"
        + "except ValueError:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_try_else_list_poisons_the_module():
    source = (
        HEAD
        + "try:\n    pass\n"
        + "except ValueError:\n    pass\n"
        + "else:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_finally_list_poisons_the_module():
    source = (
        HEAD
        + "try:\n    pass\nfinally:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_loop_body_poisons_the_module():
    source = (
        HEAD + "for _ in range(1):\n" + _fixture_class(4) + "\n" + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_while_body_poisons_the_module():
    source = (
        HEAD
        + "while True:\n"
        + _fixture_class(4)
        + "    break\n"
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_loop_else_list_poisons_the_module():
    source = (
        HEAD
        + "for _ in range(0):\n    pass\nelse:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_with_body_poisons_the_module():
    source = (
        HEAD
        + "from contextlib import nullcontext\n\n"
        + "with nullcontext():\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_match_case_poisons_the_module():
    source = (
        HEAD
        + "match 1:\n    case 1:\n"
        + _fixture_class(8)
        + "    case _:\n        pass\n"
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_inside_a_class_under_a_loop_poisons():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + "    class Outer:\n"
        + _fixture_class(8)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_under_a_loop_inside_a_class_poisons():
    source = (
        HEAD
        + "class Outer:\n"
        + "    for _ in range(1):\n"
        + _fixture_class(8)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_loop_inside_a_conditional_poisons():
    source = (
        HEAD
        + "if True:\n"
        + "    for _ in range(1):\n"
        + _fixture_class(8)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_match_case_inside_a_try_poisons():
    source = (
        HEAD
        + "try:\n"
        + "    match 1:\n"
        + "        case 1:\n"
        + _fixture_class(12)
        + "except TypeError:\n    pass\n"
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_bare_fixture_class_under_a_loop_poisons_the_module():
    source = (
        "from pytest import fixture\n\n"
        "for _ in range(1):\n"
        "    @fixture\n"
        "    class Holder:\n"
        "        pass\n"
        "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


# P4, the boundaries that stay and the partings the widening leaves.


def test_a_fixture_class_inside_a_function_under_a_loop_is_not_reached():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + "    def build():\n"
        + _fixture_class(8)
        + "        return Holder\n"
        + "\n"
        + PLAIN_TEST
    )
    _clean(source)


def test_a_fixture_class_inside_a_method_of_a_wrapped_class_is_not_reached():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + "    class Outer:\n"
        + "        def build(self):\n"
        + _fixture_class(12)
        + "            return Holder\n"
        + "\n"
        + PLAIN_TEST
    )
    _clean(source)


def test_a_plain_class_under_a_loop_poisons_nothing():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + "    class Holder:\n"
        + "        pass\n"
        + "\n"
        + PLAIN_TEST
    )
    _clean(source)


def test_a_fixture_class_under_a_false_condition_still_poisons():
    source = HEAD + "if False:\n" + _fixture_class(4) + "\n" + PLAIN_TEST
    _poisoned(source)


def test_a_fixture_class_in_an_unmatched_case_still_poisons():
    source = (
        HEAD
        + "match 2:\n    case 1:\n"
        + _fixture_class(8)
        + "    case _:\n        pass\n"
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_swallowed_by_a_handler_still_poisons():
    source = (
        HEAD
        + "try:\n"
        + "    match 1:\n"
        + "        case 1:\n"
        + _fixture_class(12)
        + "except ValueError:\n    pass\n"
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_under_an_async_loop_is_not_reached():
    source = (
        HEAD
        + "async for _ in stream:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _clean(source)


def test_findings_inside_a_poisoned_module_are_unchanged():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + _fixture_class(4)
        + "\n"
        + "def test_always():\n    assert True\n"
    )
    findings = scan_source(source, "test_client.py")
    assert [item.kind for item in findings] == ["constant_assert"]


# P3, the conftest fold.


def _loop_class_block():
    return "for _ in range(1):\n" + _fixture_class(4)


DIRECT_CLASS_BLOCK = _fixture_class(0)


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


def _kinds_and_lines(findings):
    return [(item.kind, item.line) for item in findings]


def test_a_wrapped_poisoned_conftest_contributes_nothing_to_the_fold():
    conftest = HEAD + _loop_class_block() + "\n" + (
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
    )
    findings = scan_source(
        _fetch_test(42), "test_client.py", supply_sources=[conftest]
    )
    assert findings == []


def test_a_directly_poisoned_conftest_contributes_nothing_to_the_fold():
    conftest = HEAD + DIRECT_CLASS_BLOCK + "\n" + (
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
    )
    findings = scan_source(
        _fetch_test(42), "test_client.py", supply_sources=[conftest]
    )
    assert findings == []


def test_a_poisoned_nearer_conftest_does_not_clear_a_farther_table():
    farther = (
        HEAD
        + "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
    )
    nearer = HEAD + _loop_class_block() + "\n" + (
        "@pytest.fixture\n"
        "def client():\n"
        "    return Mock()\n"
    )
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[farther, nearer],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert "conftest fixture" in findings[0].detail


def test_a_clean_nearer_conftest_still_clears_beside_a_poisoned_one():
    farther = HEAD + _loop_class_block() + "\n" + (
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
    )
    nearer = (
        HEAD
        + "@pytest.fixture\n"
        "def client():\n"
        "    return Mock()\n"
    )
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[farther, nearer],
    )
    assert findings == []
