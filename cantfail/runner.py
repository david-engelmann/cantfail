"""Run the mutation panel against a project, one mutant at a time.

Every run works on a scratch copy of the analysed project made in a
temporary directory. The analysed files are never opened for writing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .mutations import Mutant, generate_mutants
from .static_scan import StaticFinding, scan_file, test_function_names


@dataclass
class MutantOutcome:
    """The outcome of one mutant against one test file."""

    source_path: str
    mutant: Mutant
    killed: bool
    timed_out: bool = False

    def to_dict(self) -> dict:
        data = self.mutant.to_dict()
        data["source"] = self.source_path
        data["result"] = "timeout" if self.timed_out else (
            "killed" if self.killed else "survived"
        )
        return data


@dataclass
class FileVerdict:
    """The verdict for one test file."""

    path: str
    test_functions: list[str]
    baseline_ok: bool
    outcomes: list[MutantOutcome] = field(default_factory=list)

    @property
    def survivors(self) -> list[MutantOutcome]:
        return [item for item in self.outcomes if not item.killed]

    @property
    def decorative_candidate(self) -> bool:
        return (
            self.baseline_ok
            and bool(self.outcomes)
            and all(
                not item.killed and not item.timed_out
                for item in self.outcomes
            )
        )

    def to_dict(self) -> dict:
        if not self.baseline_ok:
            status = "baseline_failed"
        elif not self.outcomes:
            status = "no_applicable_mutants"
        elif self.decorative_candidate:
            status = "decorative_candidate"
        else:
            status = "can_fail"
        return {
            "path": self.path,
            "test_functions": self.test_functions,
            "status": status,
            "mutants": [item.to_dict() for item in self.outcomes],
            "surviving_mutants": [
                item.to_dict() for item in self.survivors
            ],
        }


@dataclass
class Analysis:
    """The full analysis of one project."""

    project: str
    static_findings: list[StaticFinding]
    verdicts: list[FileVerdict]

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "static_findings": [
                item.to_dict() for item in self.static_findings
            ],
            "verdicts": [item.to_dict() for item in self.verdicts],
        }


def _is_test_file(path: Path) -> bool:
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def _discover(project: Path) -> tuple[list[Path], list[Path]]:
    tests: list[Path] = []
    sources: list[Path] = []
    for path in sorted(project.rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue
        if _is_test_file(path) or path.name == "conftest.py":
            tests.append(path)
        else:
            sources.append(path)
    test_files = [path for path in tests if _is_test_file(path)]
    return test_files, sources


def _paired_sources(test_file: Path, sources: list[Path]) -> list[Path]:
    stem = test_file.name
    if stem.startswith("test_"):
        wanted = stem[len("test_"):]
    elif stem.endswith("_test.py"):
        wanted = stem[: -len("_test.py")] + ".py"
    else:
        wanted = stem
    matched = [path for path in sources if path.name == wanted]
    return matched if matched else list(sources)


def _copy_project(project: Path) -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="cantfail-"))
    target = scratch / "project"
    shutil.copytree(
        project,
        target,
        ignore=shutil.ignore_patterns(
            "__pycache__", ".git", ".pytest_cache", "*.pyc"
        ),
    )
    return target


def _run_pytest(project_copy: Path, test_file: Path, timeout: float) -> str:
    """Run one test file and return passed, failed, or timeout."""
    relative = test_file.relative_to(project_copy)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                str(relative),
            ],
            cwd=project_copy,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    return "passed" if result.returncode == 0 else "failed"


def analyse_project(project: Path, timeout: float = 30.0) -> Analysis:
    """Analyse one project directory and return the full analysis."""
    project = project.resolve()
    test_files, sources = _discover(project)

    static_findings: list[StaticFinding] = []
    for test_file in test_files:
        display = str(test_file.relative_to(project))
        static_findings.extend(scan_file(test_file, display))

    verdicts: list[FileVerdict] = []
    for test_file in test_files:
        relative_test = test_file.relative_to(project)
        functions = test_function_names(
            test_file.read_text(encoding="utf-8")
        )
        baseline_copy = _copy_project(project)
        try:
            baseline = _run_pytest(baseline_copy, baseline_copy / relative_test, timeout)
        finally:
            shutil.rmtree(baseline_copy.parent, ignore_errors=True)
        verdict = FileVerdict(
            path=str(relative_test),
            test_functions=functions,
            baseline_ok=baseline == "passed",
        )
        verdicts.append(verdict)
        if not verdict.baseline_ok:
            continue
        for source_file in _paired_sources(test_file, sources):
            relative_source = source_file.relative_to(project)
            mutants = generate_mutants(
                source_file.read_text(encoding="utf-8")
            )
            for mutant in mutants:
                mutant_copy = _copy_project(project)
                try:
                    target = mutant_copy / relative_source
                    target.write_text(mutant.source + "\n", encoding="utf-8")
                    outcome = _run_pytest(
                        mutant_copy, mutant_copy / relative_test, timeout
                    )
                finally:
                    shutil.rmtree(mutant_copy.parent, ignore_errors=True)
                verdict.outcomes.append(
                    MutantOutcome(
                        source_path=str(relative_source),
                        mutant=mutant,
                        killed=outcome == "failed",
                        timed_out=outcome == "timeout",
                    )
                )
    return Analysis(
        project=project.name,
        static_findings=static_findings,
        verdicts=verdicts,
    )
