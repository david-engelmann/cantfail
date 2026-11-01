"""Tests for the slice 8 obligations in CONTRACT.md.

Slice 8 retires the duplicate name limit FIX-24 recorded. The
scan gate reads the fixture condition on the effective
definition of a name under J1, and the helper and fixture maps
read the effective definition under J2. Every fixture here is
synthetic and written for this test file.
"""

from cantfail.settings import CollectionSettings
from cantfail.static_scan import scan_source

CHECK_SETTINGS = CollectionSettings(python_functions=("check_*",))


def _kinds_and_lines(findings):
    return [(item.kind, item.line) for item in findings]


# J1, the scan gate at module level.


def test_a_plain_definition_shadowed_by_a_fixture_earns_no_finding():
    source = (
        "import pytest\n"
        "\n"
        "def test_value():\n"
        "    assert True\n"
        "\n"
        "@pytest.fixture\n"
        "def test_value():\n"
        "    return 1\n"
        "\n"
        "def test_real():\n"
        "    assert True\n"
    )
    findings = scan_source(source, "test_value.py")
    assert _kinds_and_lines(findings) == [("constant_assert", 11)]


def test_a_fixture_definition_shadowed_by_a_plain_one_earns_findings():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "def test_value():\n"
        "    assert True\n"
        "\n"
        "def test_value():\n"
        "    assert True\n"
    )
    findings = scan_source(source, "test_value.py")
    assert _kinds_and_lines(findings) == [
        ("constant_assert", 5),
        ("constant_assert", 8),
    ]


def test_a_duplicate_with_no_fixture_keeps_the_findings_of_both_bodies():
    source = (
        "def test_value():\n"
        "    assert True\n"
        "\n"
        "def test_value():\n"
        "    assert True\n"
    )
    findings = scan_source(source, "test_value.py")
    assert _kinds_and_lines(findings) == [
        ("constant_assert", 2),
        ("constant_assert", 5),
    ]


def test_a_shadowed_plain_definition_earns_no_helper_form_finding():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def make_service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_service()\n"
        "    assert client.fetch() == 42\n"
        "\n"
        "@pytest.fixture\n"
        "def test_fetch():\n"
        "    return 1\n"
    )
    assert scan_source(source, "test_fetch.py") == []


def test_a_shadowed_plain_definition_earns_no_direct_or_self_finding():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def test_value():\n"
        "    client = Mock()\n"
        "    client.return_value = 7\n"
        "    assert client.return_value == 7\n"
        "    total = 3\n"
        "    assert total == total\n"
        "\n"
        "@pytest.fixture\n"
        "def test_value():\n"
        "    return 1\n"
    )
    assert scan_source(source, "test_value.py") == []


def test_a_shadowed_fixture_definition_earns_the_self_comparison():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "def test_value():\n"
        "    value = compute()\n"
        "    assert value == value\n"
        "\n"
        "def test_value():\n"
        "    value = compute()\n"
        "    assert value == value\n"
    )
    findings = scan_source(source, "test_value.py")
    assert _kinds_and_lines(findings) == [
        ("self_comparison", 6),
        ("self_comparison", 10),
    ]


def test_an_async_definition_shadowed_by_a_fixture_earns_no_finding():
    source = (
        "import pytest\n"
        "\n"
        "async def test_value():\n"
        "    assert True\n"
        "\n"
        "@pytest.fixture\n"
        "def test_value():\n"
        "    return 1\n"
    )
    assert scan_source(source, "test_value.py") == []


def test_the_gate_reading_holds_under_custom_settings():
    source = (
        "import pytest\n"
        "\n"
        "def check_data():\n"
        "    assert True\n"
        "\n"
        "@pytest.fixture\n"
        "def check_data():\n"
        "    return 1\n"
        "\n"
        "def check_real():\n"
        "    assert True\n"
    )
    findings = scan_source(source, "test_data.py", CHECK_SETTINGS)
    assert _kinds_and_lines(findings) == [("constant_assert", 11)]


def test_the_gate_reading_reverses_under_custom_settings():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "def check_data():\n"
        "    assert True\n"
        "\n"
        "def check_data():\n"
        "    assert True\n"
    )
    findings = scan_source(source, "test_data.py", CHECK_SETTINGS)
    assert _kinds_and_lines(findings) == [
        ("constant_assert", 5),
        ("constant_assert", 8),
    ]


# J1, the scan gate inside a class.


def test_a_plain_method_shadowed_by_a_fixture_method_earns_no_finding():
    source = (
        "import pytest\n"
        "\n"
        "class TestThing:\n"
        "    def test_value(self):\n"
        "        assert True\n"
        "\n"
        "    @pytest.fixture\n"
        "    def test_value(self):\n"
        "        return 1\n"
        "\n"
        "    def test_real(self):\n"
        "        assert True\n"
    )
    findings = scan_source(source, "test_thing.py")
    assert _kinds_and_lines(findings) == [("constant_assert", 12)]


def test_a_fixture_method_shadowed_by_a_plain_method_earns_findings():
    source = (
        "import pytest\n"
        "\n"
        "class TestThing:\n"
        "    @pytest.fixture\n"
        "    def test_value(self):\n"
        "        assert True\n"
        "\n"
        "    def test_value(self):\n"
        "        assert True\n"
    )
    findings = scan_source(source, "test_thing.py")
    assert _kinds_and_lines(findings) == [
        ("constant_assert", 6),
        ("constant_assert", 9),
    ]


def test_a_shadowed_plain_method_earns_no_helper_form_finding():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def make_service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "class TestThing:\n"
        "    def test_fetch(self):\n"
        "        client = make_service()\n"
        "        assert client.fetch() == 42\n"
        "\n"
        "    @pytest.fixture\n"
        "    def test_fetch(self):\n"
        "        return 1\n"
    )
    assert scan_source(source, "test_thing.py") == []


# J3, composition with the nested definition reading of H4.


def test_a_nested_fixture_spelling_still_belongs_to_the_test():
    source = (
        "import pytest\n"
        "\n"
        "def test_outer():\n"
        "    @pytest.fixture\n"
        "    def test_inner():\n"
        "        assert True\n"
        "\n"
        "def test_outer():\n"
        "    assert True\n"
    )
    findings = scan_source(source, "test_nested.py")
    assert _kinds_and_lines(findings) == [
        ("constant_assert", 6),
        ("constant_assert", 9),
    ]


# J2, the helper and fixture maps.


def test_a_helper_shadowed_by_a_plain_definition_supplies_nothing():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def make_service():\n"
        "    return object()\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_service()\n"
        "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_fetch.py") == []


def test_a_plain_definition_shadowed_by_a_helper_still_supplies():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_service():\n"
        "    return object()\n"
        "\n"
        "def make_service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_service()\n"
        "    assert client.fetch() == 42\n"
    )
    findings = scan_source(source, "test_fetch.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]
    assert "helper or fixture" in findings[0].detail


def test_a_helper_shadowed_by_a_fixture_supplies_the_fixture_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "def make_service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "@pytest.fixture\n"
        "def make_service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 7\n"
        "    return built\n"
        "\n"
        "def test_fetch_old():\n"
        "    client = make_service()\n"
        "    assert client.fetch() == 42\n"
        "\n"
        "def test_fetch_new():\n"
        "    client = make_service()\n"
        "    assert client.fetch() == 7\n"
        "\n"
        "def test_fetch_param(make_service):\n"
        "    assert make_service.fetch() == 7\n"
    )
    findings = scan_source(source, "test_fetch.py")
    assert _kinds_and_lines(findings) == [
        ("mock_return_value", 21),
        ("mock_return_value", 24),
    ]


def test_a_fixture_shadowed_by_a_plain_definition_supplies_its_table():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 7\n"
        "    return built\n"
        "\n"
        "def test_fetch_param(service):\n"
        "    assert service.fetch() == 42\n"
        "\n"
        "def test_fetch_bound_old():\n"
        "    client = service()\n"
        "    assert client.fetch() == 42\n"
        "\n"
        "def test_fetch_bound_new():\n"
        "    client = service()\n"
        "    assert client.fetch() == 7\n"
    )
    findings = scan_source(source, "test_fetch.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 24)]


def test_a_redefinition_replaces_the_helper_table_rather_than_merging():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_service():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def make_service():\n"
        "    built = Mock()\n"
        "    built.send.return_value = 7\n"
        "    return built\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_service()\n"
        "    assert client.fetch() == 42\n"
        "\n"
        "def test_send():\n"
        "    client = make_service()\n"
        "    assert client.send() == 7\n"
    )
    findings = scan_source(source, "test_fetch.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 19)]


# J4, the readings that stay textual.


def test_a_shadowed_class_body_is_still_read_on_its_own_methods():
    source = (
        "class TestBox:\n"
        "    def test_value(self):\n"
        "        assert True\n"
        "\n"
        "class TestBox:\n"
        "    def test_other(self):\n"
        "        assert True\n"
    )
    findings = scan_source(source, "test_box.py")
    assert _kinds_and_lines(findings) == [
        ("constant_assert", 3),
        ("constant_assert", 7),
    ]


def test_the_configured_value_map_stays_file_wide_on_a_name_match():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_service():\n"
        "    svc = Mock()\n"
        "    svc.fetch.return_value = 42\n"
        "    return svc\n"
        "\n"
        "def make_service():\n"
        "    return object()\n"
        "\n"
        "def test_fetch():\n"
        "    svc = make_service()\n"
        "    assert svc.fetch() == 42\n"
    )
    findings = scan_source(source, "test_fetch.py")
    assert _kinds_and_lines(findings) == [("mock_return_value", 13)]
    assert "helper or fixture" not in findings[0].detail
