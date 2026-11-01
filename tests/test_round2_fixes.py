"""Tests for the Round 2 review fix obligations in CONTRACT.md.

Every fixture here is synthetic and written for this test file.
"""

import json

from cantfail.report import to_json, to_text
from cantfail.runner import analyse_project
from cantfail.static_scan import selectable_test_items
from factories import write_project


def test_a_class_with_its_own_init_is_not_selected():
    source = (
        "class TestWithInit:\n"
        "    def __init__(self):\n"
        "        self.value = 1\n"
        "\n"
        "    def test_thing(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == []


def test_a_class_with_test_false_is_not_selected():
    source = (
        "class TestSkipped:\n"
        "    __test__ = False\n"
        "\n"
        "    def test_thing(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == []


def test_a_testcase_subclass_with_its_own_init_is_selected():
    source = (
        "import unittest\n"
        "\n"
        "\n"
        "class Checks(unittest.TestCase):\n"
        "    def __init__(self, method_name='runTest'):\n"
        "        super().__init__(method_name)\n"
        "\n"
        "    def test_thing(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == ["Checks::test_thing"]


def test_a_namesake_base_that_resolves_to_nothing_selects_nothing():
    source = (
        "class FakeTestCase:\n"
        "    pass\n"
        "\n"
        "\n"
        "class Checks(FakeTestCase):\n"
        "    def test_adds(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == []


def test_an_aliased_testcase_import_selects_the_subclass():
    source = (
        "from unittest import TestCase as SC\n"
        "\n"
        "\n"
        "class LocalChecks(SC):\n"
        "    def test_adds(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == ["LocalChecks::test_adds"]


def test_a_duplicate_class_name_binds_its_last_definition():
    source = (
        "class TestDup:\n"
        "    def test_first_only(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class TestDup:\n"
        "    def test_second_only(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == ["TestDup::test_second_only"]


def test_inherited_methods_are_named_under_the_collecting_class():
    source = (
        "class SharedBehaviour:\n"
        "    def test_adds(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class TestChild(SharedBehaviour):\n"
        "    def test_fetch(self):\n"
        "        pass\n"
    )
    assert selectable_test_items(source) == [
        "TestChild::test_fetch",
        "TestChild::test_adds",
    ]


INHERITED = {
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
        "class SharedBehaviour:\n"
        "    def test_adds(self):\n"
        "        assert add_one(1) == 2\n"
        "        assert add_one(0) == 1\n"
        "\n"
        "\n"
        "class TestChild(SharedBehaviour):\n"
        "    def test_fetch_returns_what_it_was_told(self):\n"
        "        client = Mock()\n"
        "        client.fetch.return_value = 42\n"
        "        result = client.fetch()\n"
        "        assert result == 42\n"
    ),
}


def test_an_inherited_strong_method_saves_the_file_headline(tmp_path):
    project = write_project(tmp_path / "inherited", INHERITED)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    by_name = {item.name: item.status for item in verdict.functions}
    assert by_name["TestChild::test_adds"] == "can_fail"
    assert (
        by_name["TestChild::test_fetch_returns_what_it_was_told"]
        == "decorative_candidate"
    )
    assert verdict.status == "can_fail"


NO_TESTS = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "def helper(value):\n"
        "    return value + 1\n"
    ),
}


def test_a_file_with_no_collectable_tests_is_not_a_failure(tmp_path):
    project = write_project(tmp_path / "notests", NO_TESTS)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is True
    assert verdict.no_tests is True
    assert verdict.status == "no_applicable_mutants"
    data = json.loads(to_json(analysis))
    (entry,) = data["verdicts"]
    assert entry["no_tests"] is True


PARTIAL = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
    ),
    "test_calc.py": (
        "from calc import add_one\n"
        "\n"
        "\n"
        "class TestOuter:\n"
        "    def test_adds(self):\n"
        "        assert add_one(1) == 2\n"
        "        assert add_one(0) == 1\n"
        "\n"
        "    class Inner:\n"
        "        def test_hidden(self):\n"
        "            assert add_one(2) == 3\n"
    ),
}


def test_a_partly_selected_file_says_so_in_both_reports(tmp_path):
    project = write_project(tmp_path / "partial", PARTIAL)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.partial_selection is True
    data = json.loads(to_json(analysis))
    (entry,) = data["verdicts"]
    assert entry["partial_selection"] is True
    assert "named items only" in to_text(analysis)


SLOW_MUTANT = {
    "nap.py": (
        "import time\n"
        "\n"
        "\n"
        "def nap():\n"
        "    time.sleep(4)\n"
    ),
    "test_nap.py": (
        "from nap import nap\n"
        "\n"
        "\n"
        "class TestNap:\n"
        "    def test_nap(self):\n"
        "        assert nap() is None\n"
    ),
}


def test_a_method_whose_mutant_run_times_out_is_inconclusive(
    tmp_path,
):
    project = write_project(tmp_path / "slowmutant", SLOW_MUTANT)
    analysis = analyse_project(project, timeout=4.6)
    verdict = analysis.verdicts[0]
    (method,) = verdict.functions
    assert method.name == "TestNap::test_nap"
    assert method.status == "inconclusive"
