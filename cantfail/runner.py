"""Run the mutation panel against a project, one mutant at a time.

Every run works on a scratch copy of the analysed project made in a
temporary directory. The analysed files are never opened for writing.

Slice 2 judges every test function on its own. The baseline for each
function runs in one shared scratch copy per test file. One scratch
copy is made per mutant and every judged function runs inside that
copy. The file level verdict is a rollup derived from the function
verdicts and never from a separate whole file mutant run.

Slice 3 widens the judged items. A selectable test method inside a
class is judged on its own beside the top level functions, selected
by its class and method node, and the rollup treats it exactly like
a function. A test file with no selectable items at all falls back
to the whole file judgement, so no file is silently skipped.

Slice 4 reads the collection naming settings of the analysed
project under F1, so discovery and selection honour the names the
project itself configured, and the analysis records any non
default settings in force for the report disclosure of F5.

Slice 5 passes those same settings to the static scan under G1,
so a static finding is a claim about a test function as the
project settings name test functions, and selection and verdicts
are untouched by the scan change under G4.

Slice 6 retires the fixture parting on the paths the selector
and the scan in the scan module provide. A fixture decorated
definition names no item and earns no verdict entry, with the
carve outs H3 states for TestCase methods and fixture decorated
classes, and a file left with fixtures alone falls to the whole
file judgement and reads as a file with no tests when its run
collects nothing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .mutations import Mutant, generate_mutants
from .settings import (
    CollectionSettings,
    file_matches,
    load_collection_settings,
)
from .static_scan import (
    StaticFinding,
    has_unselected_test_shapes,
    scan_file,
    selectable_test_items,
)


@dataclass
class MutantOutcome:
    """The outcome of one mutant against one test file or function."""

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
class FunctionVerdict:
    """The verdict for one test function."""

    name: str
    baseline_ok: bool
    outcomes: list[MutantOutcome] = field(default_factory=list)
    baseline_timed_out: bool = False

    @property
    def survivors(self) -> list[MutantOutcome]:
        return [
            item
            for item in self.outcomes
            if not item.killed and not item.timed_out
        ]

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

    @property
    def judged(self) -> bool:
        """A function is judged when mutants ran against a passing
        baseline. Timed out outcomes still count as judged runs, and
        they block a decorative verdict through the status rule."""
        return self.baseline_ok and bool(self.outcomes)

    @property
    def status(self) -> str:
        if self.baseline_timed_out:
            return "inconclusive"
        if not self.baseline_ok:
            return "baseline_failed"
        if not self.outcomes:
            return "no_applicable_mutants"
        if self.decorative_candidate:
            return "decorative_candidate"
        if any(item.killed for item in self.outcomes):
            return "can_fail"
        if any(item.timed_out for item in self.outcomes):
            return "inconclusive"
        return "can_fail"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "mutants": [item.to_dict() for item in self.outcomes],
            "surviving_mutants": [
                item.to_dict() for item in self.survivors
            ],
        }


def _aggregate_outcomes(
    functions: list[FunctionVerdict],
) -> list[MutantOutcome]:
    """Fold per function outcomes into one outcome per mutant.

    A mutant counts as killed at file level when at least one judged
    function turned red under it. A mutant counts as timed out when
    no function killed it and at least one run timed out.
    """
    order: list[tuple[str, str, int, str]] = []
    grouped: dict[tuple[str, str, int, str], list[MutantOutcome]] = {}
    for function in functions:
        for outcome in function.outcomes:
            mutant = outcome.mutant
            key = (
                outcome.source_path,
                mutant.kind,
                mutant.line,
                mutant.detail,
            )
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(outcome)
    aggregated: list[MutantOutcome] = []
    for key in order:
        items = grouped[key]
        first = items[0]
        killed = any(item.killed for item in items)
        timed_out = not killed and any(
            item.timed_out for item in items
        )
        aggregated.append(
            MutantOutcome(
                source_path=first.source_path,
                mutant=first.mutant,
                killed=killed,
                timed_out=timed_out,
            )
        )
    return aggregated


@dataclass
class FileVerdict:
    """The verdict for one test file, rolled up from its functions."""

    path: str
    test_functions: list[str]
    baseline_ok: bool
    outcomes: list[MutantOutcome] = field(default_factory=list)
    functions: list[FunctionVerdict] = field(default_factory=list)
    whole_file: bool = False
    no_tests: bool = False
    partial_selection: bool = False

    @property
    def survivors(self) -> list[MutantOutcome]:
        return [
            item
            for item in self.outcomes
            if not item.killed and not item.timed_out
        ]

    @property
    def decorative_candidate(self) -> bool:
        if self.functions and not self.whole_file:
            return self.status == "decorative_candidate"
        return (
            self.baseline_ok
            and bool(self.outcomes)
            and all(
                not item.killed and not item.timed_out
                for item in self.outcomes
            )
        )

    @property
    def status(self) -> str:
        if self.whole_file:
            # Whole file judgement, the slice 1 behaviour, kept for
            # files with no selectable test items at all, which per
            # item verdicts cannot judge. This path serves those
            # files and hand built verdicts in tests.
            if self.no_tests:
                return "no_applicable_mutants"
            if not self.baseline_ok:
                return "baseline_failed"
            if not self.outcomes:
                return "no_applicable_mutants"
            if self.decorative_candidate:
                return "decorative_candidate"
            if any(item.killed for item in self.outcomes):
                return "can_fail"
            if any(item.timed_out for item in self.outcomes):
                return "inconclusive"
            return "can_fail"
        if not self.functions and not self.outcomes:
            return "no_applicable_mutants"
        if self.functions:
            judged = [
                item for item in self.functions if item.judged
            ]
            has_baseline_failed = any(
                item.status == "baseline_failed"
                for item in self.functions
            )
            if judged and all(
                item.status == "decorative_candidate" for item in judged
            ) and not has_baseline_failed:
                return "decorative_candidate"
            if any(
                item.status == "can_fail" for item in self.functions
            ):
                return "can_fail"
            if has_baseline_failed:
                return "baseline_failed"
            if any(
                item.status == "inconclusive"
                for item in self.functions
            ):
                return "inconclusive"
            return "no_applicable_mutants"
        if not self.baseline_ok:
            return "baseline_failed"
        if not self.outcomes:
            return "no_applicable_mutants"
        if self.decorative_candidate:
            return "decorative_candidate"
        return "can_fail"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "test_functions": self.test_functions,
            "status": self.status,
            "whole_file": self.whole_file,
            "no_tests": self.no_tests,
            "partial_selection": self.partial_selection,
            "functions": [
                item.to_dict() for item in self.functions
            ],
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
    collection_settings: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            "schema": "cantfail-report/3",
            "project": self.project,
            "static_findings": [
                item.to_dict() for item in self.static_findings
            ],
            "verdicts": [item.to_dict() for item in self.verdicts],
        }
        if self.collection_settings:
            data["collection_settings"] = self.collection_settings
        return data


def _is_test_file(
    path: Path,
    settings: CollectionSettings | None = None,
    project: Path | None = None,
) -> bool:
    if settings is not None and settings.python_files is not None:
        relative = (
            path.relative_to(project).as_posix()
            if project is not None
            else path.name
        )
        return file_matches(relative, path.name, settings.python_files)
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def _discover(
    project: Path, settings: CollectionSettings | None = None
) -> tuple[list[Path], list[Path]]:
    tests: list[Path] = []
    sources: list[Path] = []
    for path in sorted(project.rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue
        if (
            _is_test_file(path, settings, project)
            or path.name == "conftest.py"
        ):
            tests.append(path)
        else:
            sources.append(path)
    test_files = [
        path for path in tests if _is_test_file(path, settings, project)
    ]
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


def _run_pytest(
    project_copy: Path,
    test_file: Path,
    timeout: float,
    item_name: str | None = None,
) -> str:
    """Run one test file or one test item in it.

    An item name is a top level function name or a class and
    method pair, and either one completes the pytest node for the
    file. Returns passed, failed, timeout, or empty, where empty is
    the exit pytest gives when it collected nothing to run.
    """
    relative = test_file.relative_to(project_copy)
    target = str(relative)
    if item_name is not None:
        target = f"{relative}::{item_name}"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                target,
            ],
            cwd=project_copy,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    if result.returncode == 0:
        return "passed"
    if result.returncode == 5:
        return "empty"
    return "failed"


def _whole_file_outcomes(
    project: Path,
    test_file: Path,
    sources: list[Path],
    timeout: float,
) -> tuple[bool, list[MutantOutcome], bool]:
    """Judge one test file as a whole, the slice 1 behaviour.

    Used for files with no selectable test items at all, so a file
    the per item verdicts cannot name is never silently skipped.
    The third value says the baseline collected nothing at all,
    which is a file with no tests in it rather than a failing one.
    """
    relative_test = test_file.relative_to(project)
    baseline_copy = _copy_project(project)
    try:
        baseline = _run_pytest(
            baseline_copy, baseline_copy / relative_test, timeout
        )
    finally:
        shutil.rmtree(baseline_copy.parent, ignore_errors=True)
    if baseline == "empty":
        return False, [], True
    if baseline != "passed":
        return False, [], False
    outcomes: list[MutantOutcome] = []
    for source_file in _paired_sources(test_file, sources):
        relative_source = source_file.relative_to(project)
        for mutant in generate_mutants(
            source_file.read_text(encoding="utf-8")
        ):
            mutant_copy = _copy_project(project)
            try:
                target = mutant_copy / relative_source
                target.write_text(
                    mutant.source + "\n", encoding="utf-8"
                )
                outcome = _run_pytest(
                    mutant_copy,
                    mutant_copy / relative_test,
                    timeout,
                )
                outcomes.append(
                    MutantOutcome(
                        source_path=str(relative_source),
                        mutant=mutant,
                        killed=outcome == "failed",
                        timed_out=outcome == "timeout",
                    )
                )
            finally:
                shutil.rmtree(
                    mutant_copy.parent, ignore_errors=True
                )
    return True, outcomes, False


def analyse_project(project: Path, timeout: float = 30.0) -> Analysis:
    """Analyse one project directory and return the full analysis."""
    project = project.resolve()
    settings = load_collection_settings(project)
    test_files, sources = _discover(project, settings)

    static_findings: list[StaticFinding] = []
    for test_file in test_files:
        display = str(test_file.relative_to(project))
        static_findings.extend(scan_file(test_file, display, settings))

    verdicts: list[FileVerdict] = []
    for test_file in test_files:
        relative_test = test_file.relative_to(project)
        source_text = test_file.read_text(encoding="utf-8")
        items = selectable_test_items(source_text, settings)
        if not items:
            whole_ok, whole_outcomes, no_tests = _whole_file_outcomes(
                project, test_file, sources, timeout
            )
            verdicts.append(
                FileVerdict(
                    path=str(relative_test),
                    test_functions=[],
                    baseline_ok=whole_ok,
                    outcomes=whole_outcomes,
                    functions=[],
                    whole_file=True,
                    no_tests=no_tests,
                )
            )
            continue
        function_verdicts: list[FunctionVerdict] = []

        baseline_copy = _copy_project(project)
        try:
            for name in items:
                baseline = _run_pytest(
                    baseline_copy,
                    baseline_copy / relative_test,
                    timeout,
                    item_name=name,
                )
                function_verdicts.append(
                    FunctionVerdict(
                        name=name,
                        baseline_ok=baseline == "passed",
                        baseline_timed_out=baseline == "timeout",
                    )
                )
        finally:
            shutil.rmtree(baseline_copy.parent, ignore_errors=True)

        judged = [
            item for item in function_verdicts if item.baseline_ok
        ]
        if judged:
            mutants: list[tuple[Path, Mutant]] = []
            for source_file in _paired_sources(test_file, sources):
                relative_source = source_file.relative_to(project)
                for mutant in generate_mutants(
                    source_file.read_text(encoding="utf-8")
                ):
                    mutants.append((relative_source, mutant))
            for relative_source, mutant in mutants:
                mutant_copy = _copy_project(project)
                try:
                    target = mutant_copy / relative_source
                    target.write_text(
                        mutant.source + "\n", encoding="utf-8"
                    )
                    for function in judged:
                        outcome = _run_pytest(
                            mutant_copy,
                            mutant_copy / relative_test,
                            timeout,
                            item_name=function.name,
                        )
                        function.outcomes.append(
                            MutantOutcome(
                                source_path=str(relative_source),
                                mutant=mutant,
                                killed=outcome == "failed",
                                timed_out=outcome == "timeout",
                            )
                        )
                finally:
                    shutil.rmtree(
                        mutant_copy.parent, ignore_errors=True
                    )

        verdict = FileVerdict(
            path=str(relative_test),
            test_functions=items,
            baseline_ok=any(
                item.baseline_ok for item in function_verdicts
            ),
            outcomes=_aggregate_outcomes(function_verdicts),
            functions=function_verdicts,
            partial_selection=has_unselected_test_shapes(
                source_text, items, settings
            ),
        )
        verdicts.append(verdict)
    return Analysis(
        project=project.name,
        static_findings=static_findings,
        verdicts=verdicts,
        collection_settings=settings.non_defaults(),
    )
