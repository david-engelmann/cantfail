"""Static fast path that flags test assertions which cannot fail.

The scan reads test files with the ast module and looks for four
shapes. A mock whose return value is assigned a value and later
asserted equal to that same value. The same shape where the mock
was configured inside a helper or a fixture in the same file and
bound to the test under another name. An assertion that compares
an expression with itself. An assertion on the constant true
value.
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


def _attribute_chain(node: ast.AST) -> tuple[str, str] | None:
    """Split a name or attribute chain into root name and the
    dotted attribute path beyond it. svc.fetch becomes the pair
    svc and fetch, and a bare name becomes the name and an empty
    path."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return node.id, ".".join(reversed(parts))
    return None


def _configured_chains(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[tuple[str, str], set[str]]:
    """Map each configured call, named by root and attribute
    chain, to the distinct literals its return value was assigned
    inside one function. svc.fetch.return_value = 42 lands under
    the pair svc and fetch."""
    configured: dict[tuple[str, str], set[str]] = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if _is_return_value(target):
                split = _attribute_chain(target.value)
                if split is not None:
                    configured.setdefault(split, set()).add(
                        ast.unparse(node.value)
                    )
    return configured


def _returned_names(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    names: list[str] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and isinstance(
            node.value, ast.Name
        ):
            names.append(node.value.id)
    return names


def _helper_and_fixture_maps(
    tree: ast.Module,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Configured values on the mocks helpers and fixtures return.

    Each helper or fixture maps to a table from attribute chain to
    the one literal configured for that call. A chain configured
    with two distinct literals inside one helper is ambiguous and
    that chain alone is left out. Other chains on the same mock
    still count.
    """
    helpers: dict[str, dict[str, str]] = {}
    fixtures: dict[str, dict[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        configured = _configured_chains(node)
        returned = set(_returned_names(node))
        table: dict[str, str] = {}
        for (root, chain), values in configured.items():
            if root in returned and len(values) == 1:
                table[chain] = next(iter(values))
        if not table:
            continue
        helpers[node.name] = table
        decorators = [ast.unparse(item) for item in node.decorator_list]
        if any("fixture" in item for item in decorators):
            fixtures[node.name] = table
    return helpers, fixtures


def _statement_lists(node: ast.AST):
    """Yield the statement lists inside a node in source order."""
    for field in ("body", "orelse", "finalbody"):
        statements = getattr(node, field, None)
        if isinstance(statements, list) and statements and isinstance(
            statements[0], ast.stmt
        ):
            yield statements


def _d5_findings_in_function(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    helpers: dict[str, dict[str, str]],
    fixtures: dict[str, dict[str, str]],
    path: str,
) -> list[StaticFinding]:
    """Helper and fixture findings inside one function scope.

    Bindings live and die inside the function that creates them. A
    name bound to a helper or fixture mock keeps that binding
    until the name is assigned something else, and only a call
    whose attribute chain matches a configured chain can be
    flagged.
    """
    findings: list[StaticFinding] = []
    env: dict[str, dict[str, str]] = {}
    for arg in func.args.args + func.args.kwonlyargs:
        if arg.arg in fixtures:
            env[arg.arg] = fixtures[arg.arg]

    def visit(statements: list[ast.stmt]) -> None:
        for statement in statements:
            if isinstance(statement, ast.Assign) and len(
                statement.targets
            ) == 1 and isinstance(statement.targets[0], ast.Name):
                name = statement.targets[0].id
                value = statement.value
                if (
                    isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id in helpers
                ):
                    env[name] = helpers[value.func.id]
                else:
                    env.pop(name, None)
            if isinstance(statement, ast.Assert):
                finding = _d5_assert_finding(statement, env, path)
                if finding is not None:
                    findings.append(finding)
            for nested in _statement_lists(statement):
                visit(nested)

    visit(func.body)
    return findings


def _d5_assert_finding(
    node: ast.Assert,
    env: dict[str, dict[str, str]],
    path: str,
) -> StaticFinding | None:
    test = node.test
    if not (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
    ):
        return None
    for side, other_node in (
        (test.left, test.comparators[0]),
        (test.comparators[0], test.left),
    ):
        if not isinstance(side, ast.Call):
            continue
        split = _attribute_chain(side.func)
        if split is None:
            continue
        root, chain = split
        table = env.get(root)
        if table is not None and table.get(chain) == ast.unparse(
            other_node
        ):
            return StaticFinding(
                kind="mock_return_value",
                path=path,
                line=node.lineno,
                detail=(
                    "assertion checks a call on a mock against "
                    "the return value that call was assigned in "
                    "a helper or fixture in the same file, "
                    f"{ast.unparse(other_node)}"
                ),
            )
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
    helpers, fixtures = _helper_and_fixture_maps(tree)

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
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            findings.extend(
                _d5_findings_in_function(node, helpers, fixtures, path)
            )
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


def top_level_test_functions(source: str) -> list[str]:
    """Return the names of test functions defined at module level.

    Per function verdicts in slice 2 cover these functions. Methods
    inside classes are not selected on their own.
    """
    tree = ast.parse(source)
    names: list[str] = []
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test")
            and node.name not in names
        ):
            names.append(node.name)
    return names


def has_class_based_tests(source: str) -> bool:
    """Return True when a class in the source defines test methods.

    A name defined twice at module level is judged once, under the
    name pytest can run, and a file carrying class based tests is
    judged at whole file level by the runner, because per function
    verdicts do not select methods.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(
                    item, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and item.name.startswith("test"):
                    return True
    return False
