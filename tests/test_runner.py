"""Tests for obligations C3, C4, C5, and C8."""

import hashlib
from pathlib import Path

from ostensible.runner import analyse_project
from factories import (
    BASELINE_FAILING,
    DECORATIVE,
    UNMATCHED_STEM,
    WELL_TESTED,
    write_project,
)


def _hashes(project: Path) -> dict[str, str]:
    return {
        str(path.relative_to(project)): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(project.rglob("*.py"))
    }


def test_well_tested_project_kills_every_applicable_mutant(tmp_path):
    project = write_project(tmp_path / "well", WELL_TESTED)
    analysis = analyse_project(project, timeout=60)
    assert len(analysis.verdicts) == 1
    verdict = analysis.verdicts[0]
    assert verdict.to_dict()["status"] == "can_fail"
    assert verdict.outcomes
    assert verdict.survivors == []
    assert {
        item.mutant.kind for item in verdict.outcomes
    } == {"return_none", "compare_invert", "constant_shift", "bool_negate"}
    assert analysis.static_findings == []


def test_decorative_project_survives_and_is_named(tmp_path):
    project = write_project(tmp_path / "decorative", DECORATIVE)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    data = verdict.to_dict()
    assert data["status"] == "decorative_candidate"
    assert verdict.outcomes
    assert len(verdict.survivors) == len(verdict.outcomes)
    assert "test_fetch_returns_what_it_was_told" in data["test_functions"]
    assert data["surviving_mutants"]
    kinds = [item.kind for item in analysis.static_findings]
    assert kinds == ["mock_return_value"]
    assert analysis.static_findings[0].path == "test_greeter.py"


def test_analysed_files_are_byte_identical_after_a_run(tmp_path):
    project = write_project(tmp_path / "pristine", DECORATIVE)
    before = _hashes(project)
    analyse_project(project, timeout=60)
    after = _hashes(project)
    assert before == after
    leftovers = [
        path
        for path in project.rglob("*")
        if path.is_file() and path.suffix == ".py"
    ]
    assert {str(p.relative_to(project)) for p in leftovers} == set(before)


def test_baseline_failure_is_never_reported_decorative(tmp_path):
    project = write_project(tmp_path / "broken", BASELINE_FAILING)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.to_dict()["status"] == "baseline_failed"
    assert verdict.decorative_candidate is False
    assert verdict.outcomes == []


def test_unmatched_stem_falls_back_to_all_source_modules(tmp_path):
    project = write_project(tmp_path / "unmatched", UNMATCHED_STEM)
    analysis = analyse_project(project, timeout=60)
    verdict = analysis.verdicts[0]
    assert verdict.outcomes
    assert {item.source_path for item in verdict.outcomes} == {"thing.py"}
