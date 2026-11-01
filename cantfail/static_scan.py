"""Static fast path that flags test assertions which cannot fail.

The scan reads test files with the ast module and looks for three
shapes. A mock whose return value is assigned a value and later
asserted equal to that same value. An assertion that compares an
expression with itself. An assertion on the constant true value.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StaticFinding:
    """One static finding in one test file."""

    kind: str
    path: str
    line: int
    detail: str

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "path": self.path,
            "line": self.line,
            "detail": self.detail,
        }


def _is_return_value(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "return_value"


def _root_name(node: ast.AST) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _call_root(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _root_name(node.func)
    return None


def scan_source(source: str, path: str) -> list[StaticFinding]:
    """Scan one test file source string and return its findings."""
    tree = ast.parse(source)
    findings: list[StaticFinding] = []

    # Map of root mock name to the source text of its assigned
    # return value, and a map of variable name to the root mock
    # it was read from.
    return_values: dict[str, str] = {}
    read_from_mock: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if _is_return_value(target):
                root = _root_name(target)
                if root is not None:
                    return_values[root] = ast.unparse(node.value)
            elif isinstance(target, ast.Name):
                root = _call_root(node.value)
                if root is not None and root in return_values:
                    read_from_mock[target.id] = root

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        if isinstance(test, ast.Constant) and test.value is True:
            findings.append(
                StaticFinding(
                    kind="constant_assert",
                    path=path,
                    line=node.lineno,
                    detail="assertion on the constant true value",
                )
            )
            continue
        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
        ):
            continue
        left = ast.unparse(test.left)
        right_node = test.comparators[0]
        right = ast.unparse(right_node)
        if left == right:
            findings.append(
                StaticFinding(
                    kind="self_comparison",
                    path=path,
                    line=node.lineno,
                    detail=f"assertion compares {left} with itself",
                )
            )
            continue
        # Direct form, assert mock.return_value == value.
        for side, other in ((test.left, right), (right_node, left)):
            if _is_return_value(side):
                root = _root_name(side)
                if root is not None and return_values.get(root) == other:
                    findings.append(
                        StaticFinding(
                            kind="mock_return_value",
                            path=path,
                            line=node.lineno,
                            detail=(
                                "assertion checks the mock return value "
                                f"against the value it was assigned, {other}"
                            ),
                        )
                    )
                    break
        else:
            # Indirect form, result = mock.call() then
            # assert result == value.
            for name_node, other in ((test.left, right), (right_node, left)):
                if isinstance(name_node, ast.Name):
                    root = read_from_mock.get(name_node.id)
                    if root is not None and return_values.get(root) == other:
                        findings.append(
                            StaticFinding(
                                kind="mock_return_value",
                                path=path,
                                line=node.lineno,
                                detail=(
                                    "assertion checks a value read from "
                                    "a mock against the return value the "
                                    f"mock was assigned, {other}"
                                ),
                            )
                        )
                        break
                root = _call_root(name_node)
                if root is not None and return_values.get(root) == other:
                    findings.append(
                        StaticFinding(
                            kind="mock_return_value",
                            path=path,
                            line=node.lineno,
                            detail=(
                                "assertion checks a call on a mock "
                                "against the return value the mock "
                                f"was assigned, {other}"
                            ),
                        )
                    )
                    break
    findings.sort(key=lambda item: (item.line, item.kind))
    return findings


def scan_file(path: Path, display_path: str) -> list[StaticFinding]:
    """Scan one test file on disk."""
    return scan_source(path.read_text(encoding="utf-8"), display_path)


def test_function_names(source: str) -> list[str]:
    """Return the names of test functions defined in a source string."""
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test"):
                names.append(node.name)
    return names
