"""Tests for the Round 13 review fixes on slice 14.

The red team and the two axis review of slice 14 left three
repairs. R13-1 qualifies the ground of P3 and pins a supplier
whose fixture decorated class a catching handler would swallow
as inert in the fold all the same. R13-2 pins the placements
P4 enumerates that slice 14 left unpinned, a failed guard, an
empty iterable loop body, a break foreclosed loop else, a
handler that never runs, an else list a raising body skips,
an elif branch, and the except star swallow. R13-3 binds the
definition stream and the fixture class reach to the one
enumeration of the descent, and the parity pins here walk both
readings over one shape per descended list.

Every fixture here is synthetic and written for this test
file. The readings were arbitrated against the installed
pytest 9.1.1 by the slice 14 probes and the review probes.
"""

from ostensible.static_scan import (
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


# R13-2, the placements P4 enumerates, pinned at the parting.


def test_a_fixture_class_under_a_failed_guard_poisons_the_module():
    source = (
        HEAD
        + "match 1:\n"
        + "    case _ if False:\n"
        + _fixture_class(8)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_an_empty_iterable_loop_body_poisons():
    source = HEAD + "for _ in []:\n" + _fixture_class(4) + "\n" + PLAIN_TEST
    _poisoned(source)


def test_a_fixture_class_in_a_break_foreclosed_loop_else_poisons():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + "    break\n"
        + "else:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_a_handler_that_never_runs_poisons():
    source = (
        HEAD
        + "try:\n"
        + "    pass\n"
        + "except ValueError:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_in_an_else_a_raising_body_skips_poisons():
    source = (
        HEAD
        + "try:\n"
        + "    raise RuntimeError('boom')\n"
        + "except RuntimeError:\n"
        + "    pass\n"
        + "else:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_under_an_elif_branch_poisons_the_module():
    source = (
        HEAD
        + "if False:\n"
        + "    pass\n"
        + "elif True:\n"
        + _fixture_class(4)
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


def test_a_fixture_class_swallowed_by_an_except_star_handler_poisons():
    source = (
        HEAD
        + "try:\n"
        + _fixture_class(4)
        + "except* ValueError:\n"
        + "    pass\n"
        + "\n"
        + PLAIN_TEST
    )
    _poisoned(source)


# R13-1, the swallowed supplier is inert in the fold.


def test_a_swallowed_poisoned_conftest_contributes_nothing_to_the_fold():
    conftest = (
        HEAD
        + "try:\n"
        + _fixture_class(4)
        + "except ValueError:\n"
        + "    pass\n"
        + "\n"
        + "@pytest.fixture\n"
        + "def client():\n"
        + "    made = Mock()\n"
        + "    made.fetch.return_value = 42\n"
        + "    return made\n"
    )
    test_source = "def test_fetch(client):\n    assert client.fetch() == 42\n"
    findings = scan_source(
        test_source, "test_client.py", supply_sources=[conftest]
    )
    assert findings == []


# R13-3, parity between the stream and the reach, one shape
# per descended list. The stream half proves a fixture standing
# in the list supplies its table to a test in the same module,
# and the reach half proves a fixture decorated class standing
# in the same list kind withholds the module.


def _supplying_fixture(indent):
    pad = " " * indent
    return (
        f"{pad}@pytest.fixture\n"
        f"{pad}def client():\n"
        f"{pad}    made = Mock()\n"
        f"{pad}    made.fetch.return_value = 42\n"
        f"{pad}    return made\n"
    )


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


def _stream_reads(wrapper):
    source = HEAD + wrapper(_supplying_fixture) + "\n" + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert [item.kind for item in findings] == ["mock_return_value"]
    other = source.replace("== 42", "== 43")
    assert scan_source(other, "test_client.py") == []


def _reach_reads(wrapper):
    source = HEAD + wrapper(_fixture_class) + "\n" + PLAIN_TEST
    _poisoned(source)


def _in_conditional_body(build):
    return "if True:\n" + build(4)


def _in_conditional_else(build):
    return "if False:\n    pass\nelse:\n" + build(4)


def _in_try_body(build):
    return "try:\n" + build(4) + "except ValueError:\n    pass\n"


def _in_handler(build):
    return "try:\n    pass\nexcept ValueError:\n" + build(4)


def _in_try_else(build):
    return (
        "try:\n    pass\nexcept ValueError:\n    pass\nelse:\n" + build(4)
    )


def _in_finally(build):
    return "try:\n    pass\nfinally:\n" + build(4)


def _in_loop_body(build):
    return "for _ in range(1):\n" + build(4)


def _in_loop_else(build):
    return "for _ in range(1):\n    pass\nelse:\n" + build(4)


def _in_with_body(build):
    return "with open(__file__) as handle:\n" + build(4)


def _in_match_case(build):
    return "match 1:\n    case 1:\n" + build(8)


_WRAPPERS = [
    _in_conditional_body,
    _in_conditional_else,
    _in_try_body,
    _in_handler,
    _in_try_else,
    _in_finally,
    _in_loop_body,
    _in_loop_else,
    _in_with_body,
    _in_match_case,
]


def test_stream_and_reach_agree_over_every_descended_list():
    for wrapper in _WRAPPERS:
        _stream_reads(wrapper)
        _reach_reads(wrapper)
