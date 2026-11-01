"""Tests for obligation C1, the static mock fast path."""

from cantfail.static_scan import scan_source


def test_direct_mock_return_value_assertion_is_flagged():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def test_direct():\n"
        "    client = Mock()\n"
        "    client.return_value = 7\n"
        "    assert client.return_value == 7\n"
    )
    findings = scan_source(source, "test_direct.py")
    kinds = [item.kind for item in findings]
    assert kinds == ["mock_return_value"]
    assert findings[0].line == 6
    assert findings[0].path == "test_direct.py"


def test_indirect_mock_return_value_assertion_is_flagged():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def test_indirect():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 42\n"
    )
    findings = scan_source(source, "test_indirect.py")
    assert [item.kind for item in findings] == ["mock_return_value"]
    assert findings[0].line == 7


def test_mock_asserted_against_a_different_value_is_not_flagged():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def test_can_fail():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 43\n"
    )
    findings = scan_source(source, "test_can_fail.py")
    assert findings == []


def test_real_result_assertion_is_not_flagged():
    source = (
        "def compute():\n"
        "    return 7\n"
        "\n"
        "def test_compute():\n"
        "    assert compute() == 7\n"
    )
    assert scan_source(source, "test_compute.py") == []


def test_self_comparison_is_flagged():
    source = (
        "def test_same():\n"
        "    total = 3\n"
        "    assert total == total\n"
    )
    findings = scan_source(source, "test_same.py")
    assert [item.kind for item in findings] == ["self_comparison"]
    assert findings[0].line == 3


def test_constant_true_assertion_is_flagged():
    source = "def test_always():\n    assert True\n"
    findings = scan_source(source, "test_always.py")
    assert [item.kind for item in findings] == ["constant_assert"]
    assert findings[0].line == 2
