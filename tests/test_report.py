"""Tests for obligations C6 and C7, the report shape and wording."""

import json

from cantfail.report import to_json, to_text
from cantfail.runner import analyse_project
from factories import DECORATIVE, write_project


def _analysis(tmp_path):
    project = write_project(tmp_path / "decorative", DECORATIVE)
    return analyse_project(project, timeout=60)


def test_json_report_carries_the_same_findings_as_the_analysis(tmp_path):
    analysis = _analysis(tmp_path)
    data = json.loads(to_json(analysis))
    assert data["project"] == "decorative"
    assert data["static_findings"][0]["kind"] == "mock_return_value"
    assert data["static_findings"][0]["path"] == "test_greeter.py"
    verdict = data["verdicts"][0]
    assert verdict["status"] == "decorative_candidate"
    assert verdict["surviving_mutants"]
    assert verdict["surviving_mutants"][0]["kind"] == "return_none"


def test_text_report_names_the_candidate_and_the_mutants(tmp_path):
    analysis = _analysis(tmp_path)
    text = to_text(analysis)
    assert "decorative candidate" in text
    assert "test_greeter.py" in text
    assert "test_fetch_returns_what_it_was_told" in text
    assert "mutant that walked through" in text
    assert "return_none" in text
    assert "mock_return_value" in text


def test_text_report_uses_conservative_wording(tmp_path):
    analysis = _analysis(tmp_path)
    text = to_text(analysis)
    assert "evidence about this fixed panel only" in text
    assert "does not prove a test is worthless" in text
    assert "does not prove a test is strong" in text
