"""Tests for the Round 12 review fixes on the slice 13 obligations.

The two axis review found two composition cells of O2 with
no pin. A wrapped table standing on the farther side of the
conftest fold, against a nearer wrapped clearer and against
a nearer wrapped table, and a wrapped definition standing
before a direct redefinition in one module, in both the
clearing and the value direction. The red team found the
binder parting O4 now states and the reach limit of the
fixture decorated class reading O3 now states. The pins
below close those cells and state those partings. The one
pin that stated the reach limit itself is renamed in slice
14 and its assertion turned to the widened reach P1 states,
the named mechanical consequence recorded there.

Every fixture here is synthetic and written for this test
file, in the shapes the slice 13 fixtures established.
"""

from ostensible.static_scan import scan_source, selectable_test_items

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


def test_a_farther_wrapped_table_clears_under_a_nearer_wrapped_bare():
    farther = HEAD + "for _ in range(1):\n" + _return_fixture(4, 42)
    nearer = HEAD + "match 1:\n    case 1:\n" + _bare_fixture(8)
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[farther, nearer],
    )
    assert findings == []


def test_a_farther_conditional_table_yields_to_a_nearer_loop_table():
    farther = HEAD + "if True:\n" + _return_fixture(4, 42)
    nearer = HEAD + "for _ in range(1):\n" + _return_fixture(4, 7)
    findings = scan_source(
        _fetch_test(7),
        "test_client.py",
        supply_sources=[farther, nearer],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert "conftest fixture" in findings[0].detail
    farther_value = _fetch_test(42)
    assert (
        scan_source(
            farther_value,
            "test_client.py",
            supply_sources=[farther, nearer],
        )
        == []
    )


def test_a_direct_bare_redefinition_clears_a_loop_fixture():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + _return_fixture(4, 42)
        + "\n"
        + _bare_fixture(0)
        + "\n"
        + _fetch_test(42)
    )
    assert scan_source(source, "test_client.py") == []


def test_a_direct_redefinition_standing_later_beats_a_match_fixture():
    source = (
        HEAD
        + "match 1:\n"
        + "    case 1:\n"
        + _return_fixture(8, 42)
        + "\n"
        + _return_fixture(0, 7)
        + "\n"
        + _fetch_test(7)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 19)]
    assert findings[0].detail.endswith(", 7")
    wrapped_value = source.replace("== 7", "== 42")
    assert scan_source(wrapped_value, "test_client.py") == []


# The binder parting O4 now states, and the FIX-23 reach limit.


def test_a_for_target_rebinding_the_fixture_name_is_not_followed():
    source = (
        HEAD
        + _return_fixture(0, 42)
        + "\n"
        + "for client in [object()]:\n    pass\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_with_as_name_rebinding_the_fixture_name_is_not_followed():
    source = (
        HEAD
        + _return_fixture(0, 42)
        + "\n"
        + "with manager as client:\n    pass\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_match_capture_rebinding_the_fixture_name_is_not_followed():
    source = (
        HEAD
        + _return_fixture(0, 42)
        + "\n"
        + "match 99:\n    case client:\n        pass\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]


def test_a_del_inside_a_wrapper_is_not_followed():
    source = (
        HEAD
        + _return_fixture(0, 42)
        + "\n"
        + "for _ in range(1):\n    del client\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_delegate_rebound_by_a_with_as_name_is_still_read():
    source = (
        HEAD
        + "def _provision():\n"
        + "    made = Mock()\n"
        + "    made.fetch.return_value = 42\n"
        + "    yield made\n"
        + "\n"
        + "with manager as _provision:\n"
        + "    @pytest.fixture\n"
        + "    def client():\n"
        + "        yield from _provision()\n"
        + "\n"
        + _fetch_test(42)
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]


def test_a_nested_fixture_configures_nothing_for_its_holder():
    source = (
        HEAD
        + "def outer():\n"
        + "    @pytest.fixture\n"
        + "    def inner():\n"
        + "        made = Mock()\n"
        + "        made.fetch.return_value = 42\n"
        + "        return made\n"
        + "\n"
        + "def test_fetch():\n"
        + "    client = outer()\n"
        + "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_nested_fixture_under_a_wrapped_helper_configures_nothing():
    source = (
        HEAD
        + "for _ in range(1):\n"
        + "    def outer():\n"
        + "        @pytest.fixture\n"
        + "        def inner():\n"
        + "            made = Mock()\n"
        + "            made.fetch.return_value = 42\n"
        + "            return made\n"
        + "\n"
        + "def test_fetch():\n"
        + "    client = outer()\n"
        + "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_helper_configuring_in_its_own_nested_block_still_flags():
    source = (
        HEAD
        + "def outer():\n"
        + "    made = Mock()\n"
        + "    if True:\n"
        + "        made.fetch.return_value = 42\n"
        + "    return made\n"
        + "\n"
        + "def test_fetch():\n"
        + "    client = outer()\n"
        + "    assert client.fetch() == 42\n"
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]


def test_a_fixture_class_under_a_loop_poisons_selection_from_slice_14():
    source = (
        "for _ in range(1):\n"
        "    @pytest.fixture\n"
        "    class Holder:\n"
        "        pass\n"
        "\n"
        "def test_plain():\n"
        "    pass\n"
    )
    assert selectable_test_items(source) == []
