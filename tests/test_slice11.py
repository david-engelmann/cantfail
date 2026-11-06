"""Tests for the slice 11 obligations in CONTRACT.md.

Slice 11 retires the yield from limit the Round 9 review
fixes recorded in L4. A fixture definition whose first
provision point is a delegation is read through its
delegate, the effective definition of the delegated name
in the same module, followed link by link, and the table
is formed from the setup part of the delegate that
finally yields, under the discipline L1 states. The
refusals of M3 and the compositions of M4 are pinned
beside the core reading.

Every fixture here is synthetic and written for this test
file. The readings were arbitrated against the installed
pytest 9.1.1 before the obligations were written, and the
probe projects behind them are the shapes the contract
preamble records.
"""

from pathlib import Path

from ostensible.runner import analyse_project
from ostensible.static_scan import scan_source


def write_project(root, files):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


DELEGATING_42 = (
    "import pytest\n"
    "from unittest.mock import Mock\n"
    "\n"
    "def _provision():\n"
    "    made = Mock()\n"
    "    made.fetch.return_value = 42\n"
    "    yield made\n"
    "\n"
    "@pytest.fixture\n"
    "def client():\n"
    "    yield from _provision()\n"
)

DELEGATING_EMPTY = (
    "import pytest\n"
    "from unittest.mock import Mock\n"
    "\n"
    "def _provision():\n"
    "    yield Mock()\n"
    "\n"
    "@pytest.fixture\n"
    "def client():\n"
    "    yield from _provision()\n"
)


def _return_fixture(value):
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


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


def _kinds_and_lines(findings):
    return [(item.kind, item.line) for item in findings]


# M1, the delegation reading.


def test_a_delegating_fixture_flags_the_fixture_form():
    findings = scan_source(
        DELEGATING_42 + "\n" + _fetch_test(42), "test_client.py"
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]
    assert "same file" in findings[0].detail
    assert findings[0].detail.endswith(", 42")


def test_a_delegating_fixture_asserted_against_another_literal_stands():
    findings = scan_source(
        DELEGATING_42 + "\n" + _fetch_test(43), "test_client.py"
    )
    assert findings == []


def test_a_delegation_chain_flags_the_last_link():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _last():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 5\n"
        "    yield made\n"
        "\n"
        "def _middle():\n"
        "    yield from _last()\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _middle()\n"
        "\n"
    ) + _fetch_test(5)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 17)]
    assert findings[0].detail.endswith(", 5")
    other = source.replace("== 5", "== 42")
    assert scan_source(other, "test_client.py") == []


def test_a_delegation_inside_a_branch_flags():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    if True:\n"
        "        yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]


def test_the_delegate_is_the_effective_definition_of_its_name():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 1\n"
        "    yield made\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 19)]
    other = source.replace("== 42", "== 1")
    assert scan_source(other, "test_client.py") == []


def test_an_own_yield_before_a_delegation_keeps_the_yield_reading():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 7\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 17)]
    other = source.replace("== 42", "== 7")
    assert scan_source(other, "test_client.py") == []


def test_a_delegation_before_a_later_yield_governs_the_reading():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 99\n"
        "    yield made\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 17)]
    other = source.replace("== 42", "== 99")
    assert scan_source(other, "test_client.py") == []


def test_a_second_delegation_provides_nothing():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _a():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "def _b():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 7\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _a()\n"
        "    yield from _b()\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 20)]
    other = source.replace("== 42", "== 7")
    assert scan_source(other, "test_client.py") == []


def test_a_delegation_without_a_call_places_no_table():
    source = DELEGATING_42.replace(
        "yield from _provision()", "yield from _provision"
    )
    assert scan_source(source + "\n" + _fetch_test(42), "t.py") == []


def test_the_delegation_table_also_lands_for_the_helper_form():
    source = DELEGATING_42 + (
        "\n"
        "def test_fetch():\n"
        "    svc = client()\n"
        "    assert svc.fetch() == 42\n"
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]
    assert "same file" in findings[0].detail


def test_an_assertion_inside_a_delegating_fixture_earns_no_finding():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    own = Mock()\n"
        "    own.fetch.return_value = 42\n"
        "    assert own.fetch() == 42\n"
        "    yield from _provision()\n"
        "\n"
        "def test_plain():\n"
        "    assert len('ab') == 2\n"
    )
    assert scan_source(source, "test_client.py") == []


# M2, how the delegate is read.


def test_the_fixtures_own_configuration_before_delegating_counts_nothing():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    own = Mock()\n"
        "    own.fetch.return_value = 99\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 16)]
    other = source.replace("== 42", "== 99")
    assert scan_source(other, "test_client.py") == []


def test_a_delegate_configuring_the_object_it_yields_flags():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision(m):\n"
        "    m.fetch.return_value = 42\n"
        "    yield m\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision(Mock())\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]


def test_an_ambiguous_chain_in_the_delegate_stays_out():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    made.fetch.return_value = 7\n"
        "    made.save.return_value = 3\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
        "\n"
        "def test_fetch(client):\n"
        "    assert client.fetch() == 42\n"
        "\n"
        "def test_save(client):\n"
        "    assert client.save() == 3\n"
    )
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 19)]


def test_teardown_configuration_in_the_delegate_earns_no_finding():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "    made.fetch.return_value = 99\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]
    other = source.replace("== 42", "== 99")
    assert scan_source(other, "test_client.py") == []


# M3, the delegates and shapes that place no table.


def test_a_fixture_decorated_delegate_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_an_async_delegate_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "async def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_a_delegation_cycle_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _a():\n"
        "    yield from _b()\n"
        "\n"
        "def _b():\n"
        "    yield from _a()\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _a()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_a_fixture_delegating_to_itself_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from client()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_an_imported_delegate_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "from helpers import gen\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from gen()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_an_attribute_delegate_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "import helpers\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from helpers.gen()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_a_delegate_returning_an_iterable_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return [made]\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_a_pass_through_delegate_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision(m):\n"
        "    yield m\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 99\n"
        "    yield from _provision(made)\n"
        "\n"
    ) + _fetch_test(99)
    assert scan_source(source, "test_client.py") == []


def test_a_plain_delegating_definition_places_no_table():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "def client():\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


# M4, composition with what already stands.


def test_a_delegating_fixture_shadowed_by_a_plain_definition():
    source = DELEGATING_42 + (
        "\n"
        "def client():\n"
        "    return Mock()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_a_returning_fixture_shadowed_by_a_delegating_definition():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 9\n"
        "    return made\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 20)]
    other = source.replace("== 42", "== 9")
    assert scan_source(other, "test_client.py") == []


def test_a_delegating_fixture_in_a_conftest_supplies_the_scan():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[DELEGATING_42],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert "conftest fixture" in findings[0].detail
    assert findings[0].detail.endswith(", 42")


def test_the_delegate_of_a_conftest_fixture_is_read_in_the_conftest():
    conftest = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 7\n"
        "    yield made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield from _provision()\n"
    )
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def _provision():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
    ) + _fetch_test(7)
    findings = scan_source(
        source, "test_client.py", supply_sources=[conftest]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 9)]
    assert "conftest fixture" in findings[0].detail
    other = source.replace("== 7", "== 42")
    assert (
        scan_source(other, "test_client.py", supply_sources=[conftest])
        == []
    )


def test_a_nearer_delegating_fixture_that_configures_nothing_clears():
    assert (
        scan_source(
            _fetch_test(42),
            "test_client.py",
            supply_sources=[_return_fixture(42), DELEGATING_EMPTY],
        )
        == []
    )


def test_a_delegating_fixture_named_like_a_test_earns_no_item(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "test_client.py": (
                "import pytest\n"
                "from unittest.mock import Mock\n"
                "\n"
                "def _provision():\n"
                "    made = Mock()\n"
                "    made.fetch.return_value = 42\n"
                "    yield made\n"
                "\n"
                "@pytest.fixture\n"
                "def test_shaped():\n"
                "    yield from _provision()\n"
                "\n"
                "def test_real():\n"
                "    assert len('ab') == 2\n"
            ),
        },
    )
    analysis = analyse_project(project)
    assert len(analysis.verdicts) == 1
    assert analysis.verdicts[0].test_functions == ["test_real"]
    assert analysis.static_findings == []


def test_an_analysis_flags_a_test_fed_by_a_conftest_delegating_fixture(
    tmp_path,
):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": DELEGATING_42,
            "test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert _kinds_and_lines(analysis.static_findings) == [
        ("mock_return_value", 2)
    ]
    assert analysis.static_findings[0].path == "test_client.py"
    assert "conftest fixture" in analysis.static_findings[0].detail
    assert len(analysis.verdicts) == 1
