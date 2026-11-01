"""Tests for the Round 9 review fixes in CONTRACT.md.

A fixture that provides its value by delegation, standing in
the yield from spelling, places no table under slice 10, as
obligation L4 now states, while an ordinary fixture in the
same file is read exactly as before.
"""

from cantfail.static_scan import scan_source


DELEGATING = (
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


def test_a_delegating_fixture_places_no_table():
    source = DELEGATING + (
        "\n"
        "def test_fetch(client):\n"
        "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_a_returning_fixture_beside_a_delegating_one_still_flags():
    source = DELEGATING + (
        "\n"
        "@pytest.fixture\n"
        "def other():\n"
        "    made = Mock()\n"
        "    made.fetch.return_value = 9\n"
        "    return made\n"
        "\n"
        "def test_other(other):\n"
        "    assert other.fetch() == 9\n"
    )
    findings = scan_source(source, "test_client.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 20)
    ]
