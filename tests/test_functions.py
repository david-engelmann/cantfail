"""Tests for slice 2 obligations D1 and D2.

D1 is per test function verdicts. D2 is the file level rollup
derived from those verdicts.
"""

from ostensible.mutations import Mutant
from ostensible.runner import (
    FileVerdict,
    FunctionVerdict,
    MutantOutcome,
    analyse_project,
)
from factories import BASELINE_MIXED, DECORATIVE, MIXED, write_project


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


def _function(name, status):
    if status == "baseline_failed":
        return FunctionVerdict(name=name, baseline_ok=False)
    if status == "no_applicable_mutants":
        return FunctionVerdict(name=name, baseline_ok=True)
    if status == "decorative_candidate":
        return FunctionVerdict(
            name=name, baseline_ok=True, outcomes=[_outcome()]
        )
    return FunctionVerdict(
        name=name, baseline_ok=True, outcomes=[_outcome(killed=True)]
    )


def _file_status(statuses):
    functions = [
        _function(f"test_{index}", status)
        for index, status in enumerate(statuses)
    ]
    verdict = FileVerdict(
        path="test_mod.py",
        test_functions=[item.name for item in functions],
        baseline_ok=True,
        functions=functions,
    )
    return verdict.status


def test_mixed_file_gives_different_verdicts_per_function(tmp_path):
    project = write_project(tmp_path / "mixed", MIXED)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    by_name = {
        item.name: item.status for item in verdict.functions
    }
    assert by_name["test_double"] == "can_fail"
    assert (
        by_name["test_fetch_returns_what_it_was_told"]
        == "decorative_candidate"
    )
    data = verdict.to_dict()
    assert data["status"] == "can_fail"
    function_data = {
        item["name"]: item["status"] for item in data["functions"]
    }
    assert function_data == by_name


def test_rollup_needs_every_judged_function_decorative():
    assert _file_status(["decorative_candidate"]) == (
        "decorative_candidate"
    )
    assert _file_status(
        ["decorative_candidate", "decorative_candidate"]
    ) == "decorative_candidate"
    assert _file_status(
        ["decorative_candidate", "can_fail"]
    ) == "can_fail"
    assert _file_status(["can_fail"]) == "can_fail"


def test_rollup_without_a_judged_function():
    assert _file_status(["baseline_failed"]) == "baseline_failed"
    assert _file_status(
        ["baseline_failed", "no_applicable_mutants"]
    ) == "baseline_failed"
    assert _file_status(["no_applicable_mutants"]) == (
        "no_applicable_mutants"
    )
    assert _file_status([]) == "no_applicable_mutants"


def test_timed_out_run_never_counts_toward_decorative():
    function = FunctionVerdict(
        name="test_slow",
        baseline_ok=True,
        outcomes=[_outcome(timed_out=True)],
    )
    assert function.decorative_candidate is False
    assert function.status == "inconclusive"
    verdict = FileVerdict(
        path="test_mod.py",
        test_functions=["test_slow"],
        baseline_ok=True,
        functions=[function],
    )
    assert verdict.status == "inconclusive"


def test_baseline_failing_function_is_never_decorative(tmp_path):
    project = write_project(tmp_path / "baselinemixed", BASELINE_MIXED)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    by_name = {
        item.name: item for item in verdict.functions
    }
    wrong = by_name["test_value_wrong"]
    assert wrong.status == "baseline_failed"
    assert wrong.decorative_candidate is False
    assert wrong.outcomes == []
    assert by_name["test_value_ok"].status == "can_fail"
    assert verdict.to_dict()["status"] == "can_fail"


def test_all_decorative_functions_roll_up_to_a_decorative_file(
    tmp_path,
):
    project = write_project(tmp_path / "decorative", DECORATIVE)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert [
        item.status for item in verdict.functions
    ] == ["decorative_candidate"]
    assert verdict.to_dict()["status"] == "decorative_candidate"
