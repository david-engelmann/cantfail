"""Tests for the Round 5 review fix obligations in CONTRACT.md.

Every fixture here is synthetic and written for this test file.
The red team probes are ported here as regression tests.
"""

from ostensible.settings import CollectionSettings
from ostensible.static_scan import (
    has_unselected_test_shapes,
    scan_source,
    selectable_test_items,
)

CHECK_SETTINGS = CollectionSettings(python_functions=("check_*",))

PLAIN_THEN_FIXTURE = (
    "import pytest\n"
    "\n"
    "def test_data():\n"
    "    assert True\n"
    "\n"
    "@pytest.fixture\n"
    "def test_data():\n"
    "    return 1\n"
    "\n"
    "def test_real():\n"
    "    assert True\n"
)

FIXTURE_THEN_PLAIN = (
    "import pytest\n"
    "\n"
    "@pytest.fixture\n"
    "def test_data():\n"
    "    return 1\n"
    "\n"
    "def test_data():\n"
    "    assert True\n"
    "\n"
    "def test_real():\n"
    "    assert True\n"
)

METHOD_PLAIN_THEN_FIXTURE = (
    "import pytest\n"
    "\n"
    "class TestBox:\n"
    "    def test_data(self):\n"
    "        assert True\n"
    "\n"
    "    @pytest.fixture\n"
    "    def test_data(self):\n"
    "        return 1\n"
    "\n"
    "    def test_real(self):\n"
    "        assert True\n"
)


def test_a_duplicate_whose_last_definition_is_a_fixture_sets_no_flag():
    items = selectable_test_items(PLAIN_THEN_FIXTURE)
    assert items == ["test_real"]
    assert has_unselected_test_shapes(PLAIN_THEN_FIXTURE, items) is False


def test_a_duplicate_whose_last_definition_is_plain_sets_no_flag():
    items = selectable_test_items(FIXTURE_THEN_PLAIN)
    assert items == ["test_data", "test_real"]
    assert has_unselected_test_shapes(FIXTURE_THEN_PLAIN, items) is False


def test_a_method_duplicate_whose_last_definition_is_a_fixture_sets_no_flag():
    items = selectable_test_items(METHOD_PLAIN_THEN_FIXTURE)
    assert items == ["TestBox::test_real"]
    assert (
        has_unselected_test_shapes(METHOD_PLAIN_THEN_FIXTURE, items)
        is False
    )


def test_a_fixture_decorated_base_poisons_the_whole_module():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "class TestBase:\n"
        "    def test_from_base(self):\n"
        "        assert True\n"
        "\n"
        "class TestChild(TestBase):\n"
        "    def test_own(self):\n"
        "        assert True\n"
    )
    assert selectable_test_items(source) == []
    assert has_unselected_test_shapes(source, []) is False


def test_a_fixture_decorated_class_beside_a_function_poisons_the_module():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "class Broken:\n"
        "    def test_method(self):\n"
        "        assert True\n"
        "\n"
        "def test_real():\n"
        "    assert True\n"
    )
    assert selectable_test_items(source) == []
    assert has_unselected_test_shapes(source, []) is False


def test_a_fixture_decorated_class_inside_a_function_poisons_nothing():
    source = (
        "import pytest\n"
        "\n"
        "def build():\n"
        "    @pytest.fixture\n"
        "    class Inner:\n"
        "        pass\n"
        "    return Inner\n"
        "\n"
        "def test_real():\n"
        "    assert True\n"
    )
    assert selectable_test_items(source) == ["test_real"]


def test_a_fixture_method_is_excluded_under_custom_function_settings():
    source = (
        "import pytest\n"
        "\n"
        "class TestBox:\n"
        "    @pytest.fixture\n"
        "    def check_data(self):\n"
        "        return 1\n"
        "\n"
        "    def check_real(self):\n"
        "        assert True\n"
    )
    assert selectable_test_items(source, CHECK_SETTINGS) == [
        "TestBox::check_real"
    ]


def test_a_shadowed_fixture_supplies_no_configured_mock():
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
        "def client():\n"
        "    return None\n"
        "\n"
        "def test_fetch(client):\n"
        "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_shadow.py") == []
