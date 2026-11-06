"""Tests for the Round 11 review fixes in CONTRACT.md.

The two axis review found that every conditional fixture
the slice 12 tests pin stands under a plain name condition,
while the preamble's probe account claims the reading is
blind to the condition's spelling across a plain name, an
attribute, a comparison, a call, and a negation. The pins
below cover the four spellings slice 12 left unpinned, each
failing on the parent head, where no conditional fixture is
read under any spelling.

Every fixture here is synthetic and written for this test
file.
"""

from ostensible.static_scan import scan_source


def _source(setup, condition):
    return (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        f"{setup}\n"
        "\n"
        f"if {condition}:\n"
        "    @pytest.fixture\n"
        "    def client():\n"
        "        made = Mock()\n"
        "        made.fetch.return_value = 42\n"
        "        return made\n"
        "\n"
        "def test_fetch(client):\n"
        "    assert client.fetch() == 42\n"
    )


def _kinds_and_lines(findings):
    return [(item.kind, item.line) for item in findings]


def test_a_fixture_under_an_attribute_condition_flags():
    source = _source('CFG = type("C", (), {"ready": True})', "CFG.ready")
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]
    other = source.replace("== 42", "== 43")
    assert scan_source(other, "test_client.py") == []


def test_a_fixture_under_a_comparison_condition_flags():
    source = _source("LEVEL = 2", "LEVEL >= 2")
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]
    other = source.replace("== 42", "== 43")
    assert scan_source(other, "test_client.py") == []


def test_a_fixture_under_a_call_condition_flags():
    source = _source("enabled = lambda: True", "enabled()")
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]
    other = source.replace("== 42", "== 43")
    assert scan_source(other, "test_client.py") == []


def test_a_fixture_under_a_negation_condition_flags():
    source = _source("DISABLED = False", "not DISABLED")
    findings = scan_source(source, "test_client.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 14)]
    other = source.replace("== 42", "== 43")
    assert scan_source(other, "test_client.py") == []
