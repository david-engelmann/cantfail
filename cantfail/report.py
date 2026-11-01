"""Render an analysis as text or as JSON."""

from __future__ import annotations

import json

from .runner import Analysis


def to_json(analysis: Analysis) -> str:
    """Render the analysis as a JSON string."""
    return json.dumps(analysis.to_dict(), indent=2, sort_keys=True)


def to_text(analysis: Analysis) -> str:
    """Render the analysis as a human readable text report."""
    lines: list[str] = []
    lines.append("cantfail report")
    lines.append(f"project - {analysis.project}")
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
        data = verdict.to_dict()
        lines.append(f"{verdict.path} - {data['status']}")
        for name in verdict.test_functions:
            lines.append(f"  test - {name}")
        if verdict.baseline_ok is False:
            lines.append(
                "  the unmutated run already fails so this file "
                "is not judged decorative"
            )
        elif not verdict.outcomes:
            lines.append("  no mutant in the fixed panel applied")
        elif verdict.decorative_candidate:
            lines.append(
                "  decorative candidate - this file stayed green "
                "under every applicable mutant in the fixed panel"
            )
            for outcome in verdict.survivors:
                mutant = outcome.mutant
                lines.append(
                    f"  mutant that walked through - "
                    f"{outcome.source_path} - {mutant.kind} "
                    f"at line {mutant.line} - {mutant.detail}"
                )
        else:
            killed = len(verdict.outcomes) - len(verdict.survivors)
            lines.append(
                f"  this file turned red under {killed} of "
                f"{len(verdict.outcomes)} mutants in the fixed panel"
            )
            for outcome in verdict.survivors:
                mutant = outcome.mutant
                lines.append(
                    f"  mutant that walked through - "
                    f"{outcome.source_path} - {mutant.kind} "
                    f"at line {mutant.line} - {mutant.detail}"
                )
    lines.append("")
    lines.append(
        "A surviving mutant is evidence about this fixed panel only. "
        "It does not prove a test is worthless and a killed mutant "
        "does not prove a test is strong."
    )
    return "\n".join(lines) + "\n"
