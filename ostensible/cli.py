"""Command line entry point for ostensible."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report import to_json, to_text
from .runner import analyse_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ostensible",
        description=(
            "Name the tests that no mutation in a fixed panel "
            "can turn red."
        ),
    )
    parser.add_argument("project", help="path to the project to analyse")
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the report as JSON instead of text",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="timeout in seconds for each single test file run",
    )
    args = parser.parse_args(argv)

    project = Path(args.project)
    if not project.is_dir():
        print(f"project directory not found - {project}", file=sys.stderr)
        return 2
    analysis = analyse_project(project, timeout=args.timeout)
    if args.json:
        print(to_json(analysis))
    else:
        print(to_text(analysis), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
