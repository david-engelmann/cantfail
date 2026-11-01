"""Tests for the slice 10 obligations in CONTRACT.md.

Slice 10 retires the yield half of the limit FIX-28 recorded
in K5. A fixture definition that yields is read from the setup
part of its body, the assignments standing before its first
yield, and the name that yield yields is the provided value,
so the fixture form of D5 flags a test that asserts the setup
literal on a yield fixture exactly as it flags one on a
returning fixture. Teardown statements after the yield
configure nothing and later yields provide nothing further.

Every fixture here is synthetic and written for this test file.
The readings were arbitrated against the installed pytest
9.1.1 before the obligations were written, and the probe
projects behind them are the shapes the contract preamble
records.
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


def _yield_fixture(value):
    return (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        f"    made.fetch.return_value = {value}\n"
        "    yield made\n"
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


YIELD_42 = _yield_fixture(42)
RETURN_9 = _return_fixture(9)

YIELD_EMPTY = (
    "import pytest\n"
    "from unittest.mock import Mock\n"
    "\n"
    "@pytest.fixture\n"
    "def client():\n"
    "    yield Mock()\n"
)


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


def _kinds_and_lines(findings):
    return [(item.kind, item.line) for item in findings]


# L1, the yield fixture reading.


def test_a_yield_fixture_flags_the_fixture_form():
    findings = scan_source(
        YIELD_42 + "\n" + _fetch_test(42), "test_client.py"
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 11)]
    assert "same file" in findings[0].detail
    assert findings[0].detail.endswith(", 42")


def test_a_yield_fixture_asserted_against_another_literal_stands():
    findings = scan_source(
        YIELD_42 + "\n" + _fetch_test(43), "test_client.py"
    )
    assert findings == []


def test_two_setup_literals_on_one_chain_stay_ambiguous():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    made.fetch.return_value = 7\n"
        "    yield made\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_a_helper_built_local_yielded_is_flagged():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def build():\n"
        "    return Mock()\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = build()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


def test_a_yield_of_a_call_places_no_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def build():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    yield build()\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_an_assertion_inside_a_yield_fixture_earns_no_finding():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    assert made.fetch() == 42\n"
        "    yield made\n"
        "\n"
        "def test_plain():\n"
        "    assert len('ab') == 2\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_fixture_that_yields_and_returns_is_read_by_its_yield():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    if True:\n"
        "        yield made\n"
        "    else:\n"
        "        return made\n"
        "    made.fetch.return_value = 99\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 15)]


# L2, teardown and later yields.


def test_teardown_configuration_earns_no_finding():
    source = YIELD_42 + "    made.fetch.return_value = 99\n" + "\n"
    assert scan_source(source + _fetch_test(99), "t.py") == []


def test_the_setup_literal_still_flags_beside_teardown():
    source = YIELD_42 + "    made.fetch.return_value = 99\n" + "\n"
    findings = scan_source(source + _fetch_test(42), "t.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 12)]
    assert findings[0].detail.endswith(", 42")


def test_a_second_yield_provides_nothing_further():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    other = Mock()\n"
        "    other.fetch.return_value = 9\n"
        "    yield made\n"
        "    yield other\n"
        "\n"
    )
    assert scan_source(source + _fetch_test(9), "t.py") == []
    findings = scan_source(source + _fetch_test(42), "t.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]


# L3, composition with what already stands.


def test_a_yield_fixture_shadowed_by_a_plain_definition():
    source = YIELD_42 + (
        "\n"
        "def client():\n"
        "    return Mock()\n"
        "\n"
    )
    assert scan_source(source + _fetch_test(42), "t.py") == []


def test_a_returning_fixture_shadowed_by_a_yield_definition():
    source = RETURN_9 + "\n" + YIELD_42.split("\n", 2)[2] + "\n"
    assert scan_source(source + _fetch_test(9), "t.py") == []
    findings = scan_source(source + _fetch_test(42), "t.py")
    assert len(findings) == 1
    assert findings[0].detail.endswith(", 42")


def test_a_conftest_yield_fixture_supplies_the_scan():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[YIELD_42],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert "conftest fixture" in findings[0].detail
    assert findings[0].detail.endswith(", 42")


def test_a_module_yield_fixture_shadows_a_conftest_returning_one():
    source = YIELD_42 + "\n" + _fetch_test(42)
    findings = scan_source(
        source, "test_client.py", supply_sources=[RETURN_9]
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 11)]
    assert "same file" in findings[0].detail
    other = YIELD_42 + "\n" + _fetch_test(9)
    assert (
        scan_source(other, "test_client.py", supply_sources=[RETURN_9])
        == []
    )


def test_a_conftest_yield_fixture_shadows_a_farther_returning_one():
    findings = scan_source(
        _fetch_test(42),
        "test_client.py",
        supply_sources=[RETURN_9, YIELD_42],
    )
    assert _kinds_and_lines(findings) == [("mock_return_value", 2)]
    assert "conftest fixture" in findings[0].detail
    assert (
        scan_source(
            _fetch_test(9),
            "test_client.py",
            supply_sources=[RETURN_9, YIELD_42],
        )
        == []
    )


def test_a_nearer_yield_fixture_that_configures_nothing_clears():
    assert (
        scan_source(
            _fetch_test(42),
            "test_client.py",
            supply_sources=[_return_fixture(42), YIELD_EMPTY],
        )
        == []
    )


def test_an_analysis_flags_a_test_fed_by_a_conftest_yield_fixture(
    tmp_path,
):
    project = write_project(
        tmp_path / "proj",
        {
            "conftest.py": YIELD_42,
            "test_client.py": _fetch_test(42),
        },
    )
    analysis = analyse_project(project)
    assert _kinds_and_lines(analysis.static_findings) == [
        ("mock_return_value", 2)
    ]
    assert analysis.static_findings[0].path == "test_client.py"
    assert len(analysis.verdicts) == 1


def test_a_yield_fixture_named_like_a_test_earns_no_item(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "test_client.py": (
                "import pytest\n"
                "from unittest.mock import Mock\n"
                "\n"
                "@pytest.fixture\n"
                "def test_shaped():\n"
                "    made = Mock()\n"
                "    made.fetch.return_value = 42\n"
                "    yield made\n"
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


# L4, what stays outside the yield reading.


def test_an_async_yield_fixture_is_outside_the_reading():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "async def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_a_plain_generator_definition_places_no_table():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def client():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    yield made\n"
        "\n"
    ) + _fetch_test(42)
    assert scan_source(source, "test_client.py") == []


def test_a_nested_yield_does_not_reach_the_return_reading():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    def gen():\n"
        "        yield 1\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 42\n"
        "    return made\n"
        "\n"
    ) + _fetch_test(42)
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]
