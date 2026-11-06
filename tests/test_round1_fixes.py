"""Tests for the Round 1 review fix obligations in CONTRACT.md.

Every fixture here is synthetic and written for this test file.
"""

from ostensible.mutations import Mutant
from ostensible.runner import (
    FileVerdict,
    FunctionVerdict,
    MutantOutcome,
    analyse_project,
)
from ostensible.static_scan import scan_source, top_level_test_functions
from factories import write_project


def _outcome(killed=False, timed_out=False):
    mutant = Mutant(
        kind="return_none", line=1, detail="return value 1", source=""
    )
    return MutantOutcome(
        source_path="mod.py",
        mutant=mutant,
        killed=killed,
        timed_out=timed_out,
    )


def test_duplicate_test_function_names_are_judged_once():
    source = (
        "def test_same():\n"
        "    assert True\n"
        "\n"
        "\n"
        "def test_same():\n"
        "    assert True\n"
        "\n"
        "\n"
        "def test_other():\n"
        "    assert True\n"
    )
    assert top_level_test_functions(source) == ["test_same", "test_other"]


def test_rollup_never_calls_a_file_decorative_over_a_broken_sibling():
    functions = [
        FunctionVerdict(
            name="test_shiny",
            baseline_ok=True,
            outcomes=[_outcome()],
        ),
        FunctionVerdict(name="test_broken", baseline_ok=False),
    ]
    verdict = FileVerdict(
        path="test_mod.py",
        test_functions=["test_shiny", "test_broken"],
        baseline_ok=True,
        functions=functions,
    )
    assert verdict.status == "baseline_failed"


def test_baseline_timeout_is_inconclusive_not_failed():
    function = FunctionVerdict(
        name="test_slow",
        baseline_ok=False,
        baseline_timed_out=True,
    )
    assert function.status == "inconclusive"
    assert function.decorative_candidate is False


def test_timed_out_mutants_are_not_listed_as_survivors():
    function = FunctionVerdict(
        name="test_slow",
        baseline_ok=True,
        outcomes=[_outcome(timed_out=True)],
    )
    assert function.survivors == []
    assert function.to_dict()["surviving_mutants"] == []


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


def test_class_only_file_is_judged_per_method(tmp_path):
    project = write_project(tmp_path / "clsonly", CLASS_ONLY)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is False
    assert verdict.status == "can_fail"
    assert [
        (item.name, item.status) for item in verdict.functions
    ] == [("TestAddOne::test_adds", "can_fail")]
    assert verdict.outcomes


CLASS_AND_TOP = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
        "\n"
        "\n"
        "def greet():\n"
        "    return 'hello'\n"
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
        "\n"
        "\n"
        "def test_fetch_returns_what_it_was_told():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 42\n"
    ),
}


def test_class_method_verdicts_stop_a_decorative_headline(
    tmp_path,
):
    project = write_project(tmp_path / "clsandtop", CLASS_AND_TOP)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.whole_file is False
    assert verdict.status == "can_fail"
    by_name = {
        item.name: item.status for item in verdict.functions
    }
    assert by_name["TestAddOne::test_adds"] == "can_fail"
    assert (
        by_name["test_fetch_returns_what_it_was_told"]
        == "decorative_candidate"
    )


def test_d5_other_method_on_the_same_mock_is_not_flagged():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_client():\n"
        "    svc = Mock()\n"
        "    svc.fetch.return_value = 'ok'\n"
        "    return svc\n"
        "\n"
        "def test_publish():\n"
        "    client = make_client()\n"
        "    assert client.publish() == 'ok'\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_d5_binding_does_not_leak_into_an_unrelated_function():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_client():\n"
        "    svc = Mock()\n"
        "    svc.fetch.return_value = 42\n"
        "    return svc\n"
        "\n"
        "def test_a():\n"
        "    client = make_client()\n"
        "    assert client.fetch() == 42\n"
        "\n"
        "def test_b():\n"
        "    assert client.fetch() == 42\n"
    )
    findings = scan_source(source, "test_client.py")
    assert [item.line for item in findings] == [10]


def test_d5_rebinding_inside_one_function_clears_the_binding():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def make_client():\n"
        "    svc = Mock()\n"
        "    svc.fetch.return_value = 42\n"
        "    return svc\n"
        "\n"
        "def test_fetch():\n"
        "    client = make_client()\n"
        "    client = RealClient()\n"
        "    assert client.fetch() == 42\n"
    )
    assert scan_source(source, "test_client.py") == []


def test_d6_call_assertions_emit_no_finding():
    source = (
        "from unittest.mock import Mock\n"
        "\n"
        "def test_fetch():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    client.fetch()\n"
        "    client.fetch.assert_called_once_with()\n"
        "    assert client.fetch.call_count == 1\n"
    )
    assert scan_source(source, "test_client.py") == []
