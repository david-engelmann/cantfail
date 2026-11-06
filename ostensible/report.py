"""Render an analysis as text or as JSON."""

from __future__ import annotations

import json

from .runner import Analysis, FileVerdict, FunctionVerdict


def to_json(analysis: Analysis) -> str:
    """Render the analysis as a JSON string."""
    return json.dumps(analysis.to_dict(), indent=2, sort_keys=True)


def _mutant_lines(outcomes, indent: str) -> list[str]:
    lines: list[str] = []
    for outcome in outcomes:
        mutant = outcome.mutant
        lines.append(
            f"{indent}mutant that walked through - "
            f"{outcome.source_path} - {mutant.kind} "
            f"at line {mutant.line} - {mutant.detail}"
        )
    return lines


def _function_lines(function: FunctionVerdict) -> list[str]:
    lines: list[str] = []
    lines.append(f"  function - {function.name} - {function.status}")
    if function.status == "baseline_failed":
        lines.append(
            "    the unmutated run of this function already fails "
            "so it is not judged decorative"
        )
    elif function.status == "no_applicable_mutants":
        lines.append(
            "    no mutant in the fixed panel applied to this "
            "function"
        )
    elif function.status == "decorative_candidate":
        lines.append(
            "    decorative candidate - this function stayed "
            "green under every applicable mutant in the fixed "
            "panel"
        )
        lines.extend(_mutant_lines(function.survivors, "    "))
    else:
        killed = len(function.outcomes) - len(function.survivors)
        lines.append(
            f"    this function turned red under {killed} of "
            f"{len(function.outcomes)} mutants in the fixed panel"
        )
        lines.extend(_mutant_lines(function.survivors, "    "))
    return lines


def _verdict_lines(verdict: FileVerdict) -> list[str]:
    lines: list[str] = []
    lines.append(f"{verdict.path} - {verdict.status}")
    for function in verdict.functions:
        lines.extend(_function_lines(function))
    if verdict.partial_selection:
        lines.append(
            "  this file holds test shaped definitions the "
            "selector does not name, and the verdict covers the "
            "named items only"
        )
    if verdict.no_tests:
        lines.append(
            "  this file holds no test pytest could collect, so "
            "no mutant in the panel has a test to be judged by"
        )
    if verdict.status == "baseline_failed":
        lines.append(
            "  the unmutated run already fails so this file "
            "is not judged decorative"
        )
    elif not verdict.outcomes:
        lines.append("  no mutant in the fixed panel applied")
    elif verdict.status == "decorative_candidate":
        lines.append(
            "  decorative candidate - every judged function in "
            "this file stayed green under every applicable mutant "
            "in the fixed panel"
        )
    else:
        killed = len(verdict.outcomes) - len(verdict.survivors)
        lines.append(
            f"  this file turned red under {killed} of "
            f"{len(verdict.outcomes)} mutants in the fixed panel"
        )
    return lines


def to_text(analysis: Analysis) -> str:
    """Render the analysis as a human readable text report."""
    lines: list[str] = []
    lines.append("cantfail report")
    lines.append(f"project - {analysis.project}")
    lines.append("schema - cantfail-report/3")
    if analysis.collection_settings:
        parts = ", ".join(
            f"{key} {' '.join(patterns)}"
            for key, patterns in analysis.collection_settings.items()
        )
        lines.append(f"collection settings - {parts}")
        if analysis.settings_source is not None:
            lines.append(
                f"collection settings source - "
                f"{analysis.settings_source}"
            )
    lines.append("")
    lines.append("static findings")
    if not analysis.static_findings:
        lines.append("none")
    for finding in analysis.static_findings:
        lines.append(
            f"{finding.path} line {finding.line} - "
            f"{finding.kind} - {finding.detail}"
        )
    lines.append("")
    lines.append("test file verdicts")
    if not analysis.verdicts:
        lines.append("no test files found")
    for verdict in analysis.verdicts:
        lines.extend(_verdict_lines(verdict))
    lines.append("")
    lines.append(
        "A surviving mutant is evidence about this fixed panel only. "
        "It does not prove a test is worthless and a killed mutant "
        "does not prove a test is strong."
    )
    return "\n".join(lines) + "\n"
