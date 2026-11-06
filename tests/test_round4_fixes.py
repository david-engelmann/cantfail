"""Tests for the Round 4 review fix obligations in CONTRACT.md.

Every fixture here is synthetic and written for this test file.
The red team probes are ported here as regression tests.
"""

from ostensible.static_scan import scan_source

HELPER = (
    "from unittest.mock import Mock\n"
    "\n"
    "def make_client():\n"
    "    svc = Mock()\n"
    "    svc.fetch.return_value = 42\n"
    "    return svc\n"
    "\n"
)


def test_a_nested_d5_assertion_is_reported_once():
    source = HELPER + (
        "def test_outer():\n"
        "    def inner():\n"
        "        client = make_client()\n"
        "        assert client.fetch() == 42\n"
        "    inner()\n"
    )
    findings = scan_source(source, "test_nested.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 11)
    ]


def test_a_d5_binding_in_the_outer_function_reaches_the_nested_one():
    source = HELPER + (
        "def test_outer():\n"
        "    client = make_client()\n"
        "    def inner():\n"
        "        assert client.fetch() == 42\n"
        "    inner()\n"
    )
    findings = scan_source(source, "test_nested.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 11)
    ]


def test_a_nested_function_with_its_own_fixture_argument_is_reported_once():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def test_outer():\n"
        "    def inner(client):\n"
        "        assert client.fetch() == 42\n"
        "    inner(client)\n"
    )
    findings = scan_source(source, "test_nested.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 12)
    ]
