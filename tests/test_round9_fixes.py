"""Tests for the Round 9 review fixes in CONTRACT.md.

A fixture that provides its value by delegation, standing in
the yield from spelling, placed no table under slice 10, as
obligation L4 then stated, while an ordinary fixture in the
same file was read exactly as before. Slice 11 retires that
limit, so the delegation pin below is corrected to the
reading M1 states, the same correction the earlier rounds
applied to a test that enshrined a retired limit.
"""

from ostensible.static_scan import scan_source


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


def test_a_delegating_fixture_is_read_through_its_delegate():
    source = DELEGATING + (
        "\n"
        "def test_fetch(client):\n"
        "    assert client.fetch() == 42\n"
    )
    findings = scan_source(source, "test_client.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 14)
    ]


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
