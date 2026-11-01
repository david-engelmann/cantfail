"""Tests for the slice 6 obligations in CONTRACT.md.

Slice 6 retires the fixture parting FIX-21 recorded. A fixture
decorated definition is not a test on the verdict path or on the
scan path, under the spellings of H2 and the carve outs of H3.
Every fixture here is synthetic and written for this test file.
"""

import json

from cantfail.report import to_json
from cantfail.runner import analyse_project
from cantfail.settings import CollectionSettings
from cantfail.static_scan import (
    has_unselected_test_shapes,
    scan_source,
    selectable_test_items,
)
from factories import write_project

CHECK_SETTINGS = CollectionSettings(python_functions=("check_*",))

SPELLINGS = (
    "import pytest\n"
    "from pytest import fixture\n"
    "\n"
    "@pytest.fixture\n"
    "def test_a():\n"
    "    return 1\n"
    "\n"
    "@pytest.fixture()\n"
    "def test_b():\n"
    "    return 2\n"
    "\n"
    "@pytest.fixture(scope='module')\n"
    "def test_c():\n"
    "    return 3\n"
    "\n"
    "@fixture\n"
    "def test_d():\n"
    "    return 4\n"
    "\n"
    "def test_real():\n"
    "    assert True\n"
)


# H1, the verdict path exclusion.


def test_fixture_functions_are_not_items_in_any_spelling():
    assert selectable_test_items(SPELLINGS) == ["test_real"]


def test_the_fixture_exclusion_holds_under_custom_settings():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "def check_data():\n"
        "    return 1\n"
        "\n"
        "def check_real():\n"
        "    assert True\n"
    )
    assert selectable_test_items(source, CHECK_SETTINGS) == [
        "check_real"
    ]


def test_a_fixture_method_is_not_an_item():
    source = (
        "import pytest\n"
        "\n"
        "class TestWidget:\n"
        "    @pytest.fixture\n"
        "    def test_data(self):\n"
        "        return 1\n"
        "\n"
        "    def test_real(self):\n"
        "        assert True\n"
    )
    assert selectable_test_items(source) == ["TestWidget::test_real"]


def test_an_inherited_fixture_method_is_not_an_item():
    source = (
        "import pytest\n"
        "\n"
        "class Base:\n"
        "    @pytest.fixture\n"
        "    def test_data(self):\n"
        "        return 1\n"
        "\n"
        "    def test_from_base(self):\n"
        "        assert True\n"
        "\n"
        "class TestChild(Base):\n"
        "    pass\n"
        "\n"
        "class TestOverride(Base):\n"
        "    def test_data(self):\n"
        "        assert True\n"
    )
    assert selectable_test_items(source) == [
        "TestChild::test_from_base",
        "TestOverride::test_data",
        "TestOverride::test_from_base",
    ]


def test_the_last_module_definition_decides_the_fixture_reading():
    fixture_last = (
        "import pytest\n"
        "\n"
        "def test_dupe():\n"
        "    assert True\n"
        "\n"
        "@pytest.fixture\n"
        "def test_dupe():\n"
        "    return 1\n"
    )
    assert selectable_test_items(fixture_last) == []
    plain_last = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "def test_dupe():\n"
        "    return 1\n"
        "\n"
        "def test_dupe():\n"
        "    assert True\n"
    )
    assert selectable_test_items(plain_last) == ["test_dupe"]


def test_the_last_method_definition_decides_the_fixture_reading():
    fixture_last = (
        "import pytest\n"
        "\n"
        "class TestDupes:\n"
        "    def test_dupe(self):\n"
        "        assert True\n"
        "\n"
        "    @pytest.fixture\n"
        "    def test_dupe(self):\n"
        "        return 1\n"
    )
    assert selectable_test_items(fixture_last) == []
    plain_last = (
        "import pytest\n"
        "\n"
        "class TestDupes:\n"
        "    @pytest.fixture\n"
        "    def test_dupe(self):\n"
        "        return 1\n"
        "\n"
        "    def test_dupe(self):\n"
        "        assert True\n"
    )
    assert selectable_test_items(plain_last) == ["TestDupes::test_dupe"]


def test_a_stacked_fixture_decorator_is_enough():
    source = (
        "import pytest\n"
        "\n"
        "def passthrough(func):\n"
        "    return func\n"
        "\n"
        "@passthrough\n"
        "@pytest.fixture\n"
        "def test_data():\n"
        "    return 1\n"
        "\n"
        "def test_real():\n"
        "    assert True\n"
    )
    assert selectable_test_items(source) == ["test_real"]


def test_a_file_of_fixtures_alone_reads_as_a_file_with_no_tests(
    tmp_path,
):
    project = write_project(
        tmp_path / "proj",
        {
            "value.py": "def value():\n    return 1\n",
            "test_value.py": (
                "import pytest\n"
                "\n"
                "\n"
                "@pytest.fixture\n"
                "def test_value():\n"
                "    assert True\n"
                "    return 1\n"
            ),
        },
    )
    analysis = analyse_project(project)
    assert len(analysis.verdicts) == 1
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is True
    assert verdict.no_tests is True
    assert verdict.status == "no_applicable_mutants"
    assert verdict.test_functions == []
    assert verdict.functions == []
    assert analysis.static_findings == []


def test_a_fixture_beside_a_test_feeds_no_verdict_counter(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "calc.py": "def add_one(x):\n    return x + 1\n",
            "test_calc.py": (
                "import pytest\n"
                "\n"
                "from calc import add_one\n"
                "\n"
                "\n"
                "@pytest.fixture\n"
                "def test_data():\n"
                "    return 1\n"
                "\n"
                "\n"
                "def test_add_one():\n"
                "    assert add_one(1) == 2\n"
                "    assert add_one(0) == 1\n"
            ),
        },
    )
    analysis = analyse_project(project)
    assert len(analysis.verdicts) == 1
    verdict = analysis.verdicts[0]
    assert verdict.test_functions == ["test_add_one"]
    assert [item.name for item in verdict.functions] == ["test_add_one"]
    assert verdict.partial_selection is False
    assert verdict.status == "can_fail"


# H2, the spellings and the one reading.


def test_lookalike_decorators_are_not_fixture_decorators():
    source = (
        "import pytest\n"
        "\n"
        "@other.fixture\n"
        "def test_a():\n"
        "    assert True\n"
        "\n"
        "@pytest.fixturex\n"
        "def test_b():\n"
        "    assert True\n"
    )
    assert selectable_test_items(source) == ["test_a", "test_b"]


def test_a_project_defined_fixture_spelling_is_read_as_a_fixture():
    source = (
        "def fixture(func):\n"
        "    return func\n"
        "\n"
        "@fixture\n"
        "def test_data():\n"
        "    return 1\n"
        "\n"
        "def test_real():\n"
        "    assert True\n"
    )
    assert selectable_test_items(source) == ["test_real"]


def test_a_lookalike_decorator_does_not_make_a_fixture_for_the_scan():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixturex\n"
        "def client():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def test_fetch(client):\n"
        "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_fetch.py") == []


# H3, where the exclusion does not reach on the verdict path.


def test_a_testcase_fixture_method_keeps_its_item():
    source = (
        "from unittest import TestCase\n"
        "import pytest\n"
        "\n"
        "class Cases(TestCase):\n"
        "    @pytest.fixture\n"
        "    def test_fix(self):\n"
        "        return 1\n"
        "\n"
        "    def test_plain(self):\n"
        "        assert True\n"
    )
    assert selectable_test_items(source) == [
        "Cases::test_fix",
        "Cases::test_plain",
    ]


def test_a_fixture_decorated_class_yields_no_items():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "class TestGear:\n"
        "    def test_m(self):\n"
        "        assert True\n"
        "\n"
        "def test_real():\n"
        "    assert True\n"
    )
    assert selectable_test_items(source) == []


# H4, the scan path exclusion.


def test_assertions_inside_a_fixture_earn_no_finding():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def test_data():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 42\n"
        "    assert True\n"
        "\n"
        "def test_real():\n"
        "    assert True\n"
    )
    findings = scan_source(source, "test_data.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("constant_assert", 13)
    ]


def test_the_scan_exclusion_holds_under_custom_settings():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "def check_data():\n"
        "    assert True\n"
        "\n"
        "def check_real():\n"
        "    assert True\n"
    )
    findings = scan_source(source, "test_data.py", CHECK_SETTINGS)
    assert [(item.kind, item.line) for item in findings] == [
        ("constant_assert", 8)
    ]


def test_a_fixture_method_earns_no_finding():
    source = (
        "import pytest\n"
        "\n"
        "class Plain:\n"
        "    @pytest.fixture\n"
        "    def test_m(self):\n"
        "        assert True\n"
        "\n"
        "    def test_n(self):\n"
        "        assert True\n"
    )
    findings = scan_source(source, "test_methods.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("constant_assert", 9)
    ]


def test_a_nested_fixture_spelling_still_belongs_to_the_test():
    source = (
        "def test_outer():\n"
        "    @pytest.fixture\n"
        "    def test_inner():\n"
        "        assert True\n"
    )
    findings = scan_source(source, "test_nested.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("constant_assert", 4)
    ]


def test_a_class_decorator_reaches_nothing_on_the_scan_path():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "class Gear:\n"
        "    def test_m(self):\n"
        "        assert True\n"
    )
    findings = scan_source(source, "test_gear.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("constant_assert", 6)
    ]


# H5, the fixture still serving as a fixture.


def test_a_test_named_fixture_still_supplies_its_mock():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture\n"
        "def test_client():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def test_fetch(test_client):\n"
        "    assert test_client.fetch() == 42\n"
    )
    findings = scan_source(source, "test_fetch.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 11)
    ]
    assert "helper or fixture" in findings[0].detail
    assert selectable_test_items(source) == ["test_fetch"]


def test_a_called_fixture_spelling_still_supplies_its_mock():
    source = (
        "import pytest\n"
        "from unittest.mock import Mock\n"
        "\n"
        "@pytest.fixture()\n"
        "def test_client():\n"
        "    built = Mock()\n"
        "    built.fetch.return_value = 42\n"
        "    return built\n"
        "\n"
        "def test_fetch(test_client):\n"
        "    assert test_client.fetch() == 42\n"
    )
    findings = scan_source(source, "test_fetch.py")
    assert [(item.kind, item.line) for item in findings] == [
        ("mock_return_value", 11)
    ]
    assert selectable_test_items(source) == ["test_fetch"]


# H6, the partial selection accounting.


def test_a_fixture_beside_a_test_is_not_an_unselected_shape():
    source = (
        "import pytest\n"
        "\n"
        "@pytest.fixture\n"
        "def test_data():\n"
        "    assert True\n"
        "\n"
        "def test_real():\n"
        "    assert True\n"
    )
    assert (
        has_unselected_test_shapes(source, ["test_real"]) is False
    )
    control = (
        "def test_a():\n"
        "    assert True\n"
        "\n"
        "def test_b():\n"
        "    assert True\n"
    )
    assert has_unselected_test_shapes(control, ["test_a"]) is True


def test_a_fixture_method_is_not_an_unselected_shape():
    source = (
        "import pytest\n"
        "\n"
        "class TestWidget:\n"
        "    @pytest.fixture\n"
        "    def test_data(self):\n"
        "        return 1\n"
        "\n"
        "    def test_real(self):\n"
        "        assert True\n"
    )
    assert (
        has_unselected_test_shapes(source, ["TestWidget::test_real"])
        is False
    )


# H7, the report format decision.


def test_the_schema_stays_at_format_3_on_a_fixture_project(tmp_path):
    project = write_project(
        tmp_path / "proj",
        {
            "value.py": "def value():\n    return 1\n",
            "test_value.py": (
                "import pytest\n"
                "\n"
                "\n"
                "@pytest.fixture\n"
                "def test_value():\n"
                "    return 1\n"
            ),
        },
    )
    data = json.loads(to_json(analyse_project(project)))
    assert data["schema"] == "cantfail-report/3"
    entry = data["verdicts"][0]
    assert entry["test_functions"] == []
    assert entry["functions"] == []
    assert entry["no_tests"] is True
