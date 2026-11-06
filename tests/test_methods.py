"""Tests for slice 3 obligations E1 to E7.

E1 to E7 cover per method verdicts for class based tests, the
selection rule, the amended whole file fallback, the rollup over
methods, the report format, duplicate method names, and the
stated limits of selection. Every fixture here is synthetic and
written for this test file.
"""

import json

from ostensible.report import to_json, to_text
from ostensible.runner import analyse_project
from ostensible.static_scan import selectable_test_items
from factories import write_project


def test_items_name_top_level_functions_and_methods_in_order():
    source = (
        "def test_first():\n"
        "    assert True\n"
        "\n"
        "\n"
        "class TestGroup:\n"
        "    def test_member(self):\n"
        "        assert True\n"
        "\n"
        "    def helper(self):\n"
        "        return 1\n"
        "\n"
        "\n"
        "def test_last():\n"
        "    assert True\n"
    )
    assert selectable_test_items(source) == [
        "test_first",
        "TestGroup::test_member",
        "test_last",
    ]


def test_items_include_a_testcase_class_under_any_name():
    source = (
        "import unittest\n"
        "\n"
        "\n"
        "class AdditionChecks(unittest.TestCase):\n"
        "    def test_adds(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class CustomTestCase(unittest.TestCase):\n"
        "    pass\n"
        "\n"
        "\n"
        "class MoreChecks(CustomTestCase):\n"
        "    def test_more(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == [
        "AdditionChecks::test_adds",
        "MoreChecks::test_more",
    ]


def test_items_skip_classes_pytest_would_not_collect():
    source = (
        "class Helpers:\n"
        "    def test_ignored(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class TestOuter:\n"
        "    class TestInner:\n"
        "        def test_deep(self):\n"
        "            pass\n"
    )
    assert selectable_test_items(source) == []


def test_items_judge_a_duplicate_method_once_per_class():
    source = (
        "class TestDup:\n"
        "    def test_same(self):\n"
        "        pass\n"
        "\n"
        "    def test_same(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class TestOther:\n"
        "    def test_same(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == [
        "TestDup::test_same",
        "TestOther::test_same",
    ]


CLASS_MIXED = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from unittest.mock import Mock\n"
        "\n"
        "from calc import add_one\n"
        "\n"
        "\n"
        "class TestAddOne:\n"
        "    def test_adds(self):\n"
        "        assert add_one(1) == 2\n"
        "        assert add_one(0) == 1\n"
        "\n"
        "    def test_fetch_returns_what_it_was_told(self):\n"
        "        client = Mock()\n"
        "        client.fetch.return_value = 42\n"
        "        result = client.fetch()\n"
        "        assert result == 42\n"
    ),
}


def test_one_class_holds_a_strong_and_a_decorative_method(tmp_path):
    project = write_project(tmp_path / "classmixed", CLASS_MIXED)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is False
    by_name = {
        item.name: item.status for item in verdict.functions
    }
    assert by_name["TestAddOne::test_adds"] == "can_fail"
    assert (
        by_name["TestAddOne::test_fetch_returns_what_it_was_told"]
        == "decorative_candidate"
    )
    assert verdict.to_dict()["status"] == "can_fail"
    assert verdict.to_dict()["test_functions"] == [
        "TestAddOne::test_adds",
        "TestAddOne::test_fetch_returns_what_it_was_told",
    ]


CLASS_ONLY = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from calc import add_one\n"
        "\n"
        "\n"
        "class TestAddOne:\n"
        "    def test_adds(self):\n"
        "        assert add_one(1) == 2\n"
        "        assert add_one(0) == 1\n"
    ),
}


def test_class_only_file_is_judged_per_method_not_whole_file(
    tmp_path,
):
    project = write_project(tmp_path / "classonly", CLASS_ONLY)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is False
    assert [
        item.name for item in verdict.functions
    ] == ["TestAddOne::test_adds"]
    assert verdict.functions[0].status == "can_fail"
    assert verdict.status == "can_fail"


TESTCASE_STYLE = {
    "counter.py": (
        "def value():\n"
        "    return 1\n"
    ),
    "test_counter.py": (
        "import unittest\n"
        "\n"
        "from counter import value\n"
        "\n"
        "\n"
        "class ValueChecks(unittest.TestCase):\n"
        "    def test_value(self):\n"
        "        self.assertEqual(value(), 1)\n"
    ),
}


def test_unittest_testcase_methods_are_judged_on_their_own(
    tmp_path,
):
    project = write_project(tmp_path / "testcase", TESTCASE_STYLE)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is False
    assert [
        (item.name, item.status) for item in verdict.functions
    ] == [("ValueChecks::test_value", "can_fail")]


METHOD_BASELINE_MIXED = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from unittest.mock import Mock\n"
        "\n"
        "from calc import add_one\n"
        "\n"
        "\n"
        "class TestAddOne:\n"
        "    def test_adds_wrong(self):\n"
        "        assert add_one(1) == 3\n"
        "\n"
        "    def test_fetch_returns_what_it_was_told(self):\n"
        "        client = Mock()\n"
        "        client.fetch.return_value = 42\n"
        "        result = client.fetch()\n"
        "        assert result == 42\n"
    ),
}


def test_baseline_failing_method_blocks_a_decorative_headline(
    tmp_path,
):
    project = write_project(
        tmp_path / "methodbaseline", METHOD_BASELINE_MIXED
    )
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    by_name = {
        item.name: item for item in verdict.functions
    }
    wrong = by_name["TestAddOne::test_adds_wrong"]
    assert wrong.status == "baseline_failed"
    assert wrong.decorative_candidate is False
    assert wrong.outcomes == []
    assert (
        by_name["TestAddOne::test_fetch_returns_what_it_was_told"]
        .status
        == "decorative_candidate"
    )
    assert verdict.to_dict()["status"] == "baseline_failed"


DUPLICATE_METHOD = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from unittest.mock import Mock\n"
        "\n"
        "from calc import add_one\n"
        "\n"
        "\n"
        "class TestAddOne:\n"
        "    def test_adds(self):\n"
        "        client = Mock()\n"
        "        client.fetch.return_value = 42\n"
        "        result = client.fetch()\n"
        "        assert result == 42\n"
        "\n"
        "    def test_adds(self):\n"
        "        assert add_one(1) == 2\n"
    ),
}


def test_a_duplicate_method_is_judged_once_as_pytest_runs_it(
    tmp_path,
):
    project = write_project(tmp_path / "dupmethod", DUPLICATE_METHOD)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    entries = [
        item for item in verdict.functions
        if item.name == "TestAddOne::test_adds"
    ]
    assert len(entries) == 1
    assert entries[0].status == "can_fail"


SLOW_METHOD = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "import time\n"
        "\n"
        "\n"
        "class TestSlow:\n"
        "    def test_sleeps(self):\n"
        "        time.sleep(30)\n"
    ),
}


def test_a_method_whose_baseline_times_out_is_inconclusive(
    tmp_path,
):
    project = write_project(tmp_path / "slowmethod", SLOW_METHOD)
    analysis = analyse_project(project, timeout=2)
    verdict = analysis.verdicts[0]
    assert [
        (item.name, item.status) for item in verdict.functions
    ] == [("TestSlow::test_sleeps", "inconclusive")]
    assert verdict.status == "inconclusive"


NO_ITEMS = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from calc import add_one\n"
        "\n"
        "\n"
        "class Helpers:\n"
        "    def test_adds(self):\n"
        "        assert add_one(1) == 2\n"
    ),
}


def test_a_file_with_no_selectable_items_uses_the_whole_file_path(
    tmp_path,
):
    project = write_project(tmp_path / "noitems", NO_ITEMS)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is True
    assert verdict.functions == []
    assert verdict.status == "no_applicable_mutants"


def test_reports_show_method_entries_like_function_entries(
    tmp_path,
):
    project = write_project(tmp_path / "classmixed", CLASS_MIXED)
    analysis = analyse_project(project, timeout=60)
    text = to_text(analysis)
    assert "schema - cantfail-report/3" in text
    assert "function - TestAddOne::test_adds - can_fail" in text
    assert (
        "function - TestAddOne::test_fetch_returns_what_it_was_told"
        " - decorative_candidate"
    ) in text
    data = json.loads(to_json(analysis))
    assert data["schema"] == "cantfail-report/3"
    names = [
        item["name"] for item in data["verdicts"][0]["functions"]
    ]
    assert names == [
        "TestAddOne::test_adds",
        "TestAddOne::test_fetch_returns_what_it_was_told",
    ]
