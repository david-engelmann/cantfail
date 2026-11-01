"""Tests for the command line entry point."""

import json

from cantfail.cli import main
from factories import DECORATIVE, write_project


def test_cli_prints_a_text_report(tmp_path, capsys):
    project = write_project(tmp_path / "decorative", DECORATIVE)
    exit_code = main([str(project), "--timeout", "60"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "cantfail report" in out
    assert "decorative candidate" in out


def test_cli_prints_a_json_report_with_the_json_flag(tmp_path, capsys):
    project = write_project(tmp_path / "decorative", DECORATIVE)
    exit_code = main([str(project), "--json", "--timeout", "60"])
    out = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(out)
    assert data["verdicts"][0]["status"] == "decorative_candidate"


def test_cli_rejects_a_missing_project(tmp_path, capsys):
    exit_code = main([str(tmp_path / "missing")])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "not found" in captured.err
