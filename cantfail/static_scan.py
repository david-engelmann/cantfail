"""Static fast path that flags test assertions which cannot fail.

The scan reads test files with the ast module and looks for four
shapes. A mock whose return value is assigned a value and later
asserted equal to that same value. The same shape where the mock
was configured inside a helper or a fixture in the same file and
bound to the test under another name. An assertion that compares
an expression with itself. An assertion on the constant true
value.

Slice 5 gates every shape on the assertion sitting inside a test
function, where what counts as a test function follows the
python_functions setting of the analysed project under G2. The
maps the scan builds stay file wide, because a helper is not a
test function and is never required to be one for the test that
binds its mock to be flagged.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .settings import (
    DEFAULT_SETTINGS,
    CollectionSettings,
    name_matches,
)


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
    flagged. A nested function is visited exactly once, with a
    copy of the enclosing bindings plus its own fixture arguments,
    the way a closure reads the enclosing scope, so an assertion
    inside it is reported once and never once per enclosing call.
    """
    findings: list[StaticFinding] = []
    env: dict[str, dict[str, str]] = {}
    for arg in func.args.args + func.args.kwonlyargs:
        if arg.arg in fixtures:
            env[arg.arg] = fixtures[arg.arg]

    def visit(
        statements: list[ast.stmt], env: dict[str, dict[str, str]]
    ) -> None:
        for statement in statements:
            if isinstance(
                statement, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                child = dict(env)
                for arg in statement.args.args + statement.args.kwonlyargs:
                    if arg.arg in fixtures:
                        child[arg.arg] = fixtures[arg.arg]
                visit(statement.body, child)
                continue
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
                visit(nested, env)

    visit(func.body, env)
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


def _parent_map(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    """Map each node in a parsed file to its parent node."""
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _governing_function(
    node: ast.AST, parents: dict[ast.AST, ast.AST]
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the function definition a node belongs to for the
    scan, under the rule of G2.

    The governing definition is the one on the climb from the node
    to the module that sits at module level or directly inside a
    module level class. A definition nested any deeper belongs to
    that governing definition, and a node outside every such
    definition has none.
    """
    current: ast.AST | None = node
    while current is not None:
        if isinstance(
            current, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            parent = parents.get(current)
            if isinstance(parent, ast.Module):
                return current
            if isinstance(parent, ast.ClassDef) and isinstance(
                parents.get(parent), ast.Module
            ):
                return current
        current = parents.get(current)
    return None


def scan_source(
    source: str,
    path: str,
    settings: CollectionSettings | None = None,
) -> list[StaticFinding]:
    """Scan one test file source string and return its findings.

    The settings argument carries the collection naming settings
    of the analysed project under G1, the way the selector takes
    them, and the defaults are in force when it is not given. A
    finding is reported only for an assertion that sits inside a
    test function under G2, decided by the python_functions
    setting in force through the same matching rule the selector
    applies to that setting.
    """
    if settings is None:
        settings = DEFAULT_SETTINGS
    tree = ast.parse(source)
    parents = _parent_map(tree)

    def in_test_function(node: ast.AST) -> bool:
        governing = _governing_function(node, parents)
        return governing is not None and _function_name_matches(
            governing.name, settings
        )

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
        if not in_test_function(node):
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
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _governing_function(node, parents) is node
            and in_test_function(node)
        ):
            findings.extend(
                _d5_findings_in_function(node, helpers, fixtures, path)
            )
    findings.sort(key=lambda item: (item.line, item.kind))
    return findings


def scan_file(
    path: Path,
    display_path: str,
    settings: CollectionSettings | None = None,
) -> list[StaticFinding]:
    """Scan one test file on disk, under the settings of G1."""
    return scan_source(
        path.read_text(encoding="utf-8"), display_path, settings
    )


def test_function_names(source: str) -> list[str]:
    """Return the names of test functions defined in a source string.

    Legacy helper kept for its original callers. It reads the bare
    test prefix and does not follow the collection naming settings
    the scan and the selector have honoured since slice 4, and it
    is not used on the analysis path.
    """
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
    inside classes are not selected on their own by this helper,
    and a name defined twice is returned once, under the single
    name pytest can run.

    Legacy helper kept for its original callers. It reads the bare
    test prefix and does not follow the collection naming settings
    the scan and the selector have honoured since slice 4, and it
    is not used on the analysis path.
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


def _unittest_bindings(tree):
    """Names in this module that refer to unittest and its TestCase.

    Returns a pair of the local names bound to the TestCase class
    itself and the local names bound to the unittest module.
    """
    testcase_names = set()
    module_names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "unittest":
                    module_names.add(alias.asname or "unittest")
        elif isinstance(node, ast.ImportFrom):
            if node.module in ("unittest", "unittest.case"):
                for alias in node.names:
                    if alias.name == "TestCase":
                        testcase_names.add(alias.asname or "TestCase")
    return testcase_names, module_names


def _is_testcase_class(node, classes, bindings, seen):
    """Return True when a class resolves to a unittest TestCase.

    Resolution follows the names the module itself binds. A base
    counts when it is a bound TestCase name, the TestCase attribute
    of a bound unittest module, or a local class that itself
    resolves to a TestCase. A name that merely ends in TestCase and
    resolves to nothing here does not count.
    """
    testcase_names, module_names = bindings
    if id(node) in seen:
        return False
    seen = seen | {id(node)}
    for base in node.bases:
        if isinstance(base, ast.Name):
            if base.id in testcase_names:
                return True
            local = classes.get(base.id)
            if local is not None and _is_testcase_class(
                local, classes, bindings, seen
            ):
                return True
        elif isinstance(base, ast.Attribute):
            if (
                base.attr == "TestCase"
                and isinstance(base.value, ast.Name)
                and base.value.id in module_names
            ):
                return True
    return False


def _sets_test_false(node):
    for member in node.body:
        if isinstance(member, ast.Assign):
            for target in member.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__test__"
                    and isinstance(member.value, ast.Constant)
                    and member.value.value is False
                ):
                    return True
    return False


def _defines_init(node):
    return any(
        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and member.name == "__init__"
        for member in node.body
    )


def _function_name_matches(name, settings):
    """Return True when a function or method name is an item name
    under the python_functions setting in force, or under the
    default test prefix when no such setting is in force."""
    if settings.python_functions is None:
        return name.startswith("test")
    return name_matches(name, settings.python_functions)


def _class_yields_methods(node, classes, bindings, settings):
    """Return True when the selector names methods of this class.

    The rules match what pytest collects, under the settings in
    force. A class that resolves to a unittest TestCase yields its
    methods under any name. A name based class yields its methods
    unless it defines an init of its own, which makes pytest
    refuse it. The name rule is the python_classes setting in
    force when one is set, with its patterns replacing the Test
    prefix entirely, and the Test prefix itself when no setting
    is in force. A class that sets __test__ to False yields
    nothing, whatever its name or bases.
    """
    if _sets_test_false(node):
        return False
    if _is_testcase_class(node, classes, bindings, frozenset()):
        return True
    if _defines_init(node):
        return False
    if settings.python_classes is not None:
        return name_matches(node.name, settings.python_classes)
    return node.name.startswith("Test")


def _test_method_names(node, classes, seen, settings):
    """Test method names of a class, its own first, then inherited.

    A name counts as a test method name under the matching rule of
    _function_name_matches. Inherited names come from local base
    classes in base order, skipping any name the class or an
    earlier base already gave.
    """
    names = []
    for member in node.body:
        if (
            isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _function_name_matches(member.name, settings)
            and member.name not in names
        ):
            names.append(member.name)
    if id(node) in seen:
        return names
    seen = seen | {id(node)}
    for base in node.bases:
        if isinstance(base, ast.Name):
            local = classes.get(base.id)
            if local is not None:
                for name in _test_method_names(
                    local, classes, seen, settings
                ):
                    if name not in names:
                        names.append(name)
    return names


def selectable_test_items(
    source: str, settings: CollectionSettings | None = None
) -> list[str]:
    """Return the selectable test items of a file in source order.

    An item is the selector pytest uses below the file. A top level
    test function is named by its own name. A test method inside a
    class the collection rules in force would collect is named by
    its class and its method joined the way a pytest node joins
    them, and methods inherited from a local base class are named
    under the class pytest collects them on. Each selector appears
    once, so a function or a method defined twice is judged once,
    under the single node pytest can run, while the same method
    name in two classes names two different items. A class name
    defined twice binds its last definition, exactly as the module
    does, and only that definition yields items. Classes nested
    inside other classes are not selected. The settings argument
    carries the collection naming settings of F1 to F3, and the
    defaults are in force when it is not given.
    """
    if settings is None:
        settings = DEFAULT_SETTINGS
    tree = ast.parse(source)
    bindings = _unittest_bindings(tree)
    classes = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes[node.name] = node
    items: list[str] = []
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ) and _function_name_matches(node.name, settings):
            if node.name not in items:
                items.append(node.name)
        elif (
            isinstance(node, ast.ClassDef)
            and classes.get(node.name) is node
            and _class_yields_methods(node, classes, bindings, settings)
        ):
            for name in _test_method_names(
                node, classes, frozenset(), settings
            ):
                selector = f"{node.name}::{name}"
                if selector not in items:
                    items.append(selector)
    return items


def _shaped_name(name, settings):
    """Return True when a definition name reads as test shaped for
    the disclosure of FIX-12. A name is test shaped under the
    python_functions setting in force when one is set, its
    patterns replacing the test prefix entirely, and under the
    test prefix when no setting is in force, so a name the
    project's own settings have deselected never reads as an
    unjudged test shape."""
    if settings.python_functions is not None:
        return name_matches(name, settings.python_functions)
    return name.startswith("test")


def has_unselected_test_shapes(
    source: str,
    items: list[str],
    settings: CollectionSettings | None = None,
) -> bool:
    """Return True when a file holds test shaped definitions that
    the selector did not name, beside at least one named item.

    Test shaped means a top level function or a method in any class
    in the file, nested classes included, whose name is test shaped
    under _shaped_name. The count compares distinct runnable
    names, so inherited methods named under a subclass do not read
    as unselected.
    """
    if settings is None:
        settings = DEFAULT_SETTINGS
    tree = ast.parse(source)
    shaped = 0
    top_level = set()
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ) and _shaped_name(node.name, settings):
            top_level.add(node.name)
    shaped += len(top_level)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = {
                member.name
                for member in node.body
                if isinstance(
                    member, (ast.FunctionDef, ast.AsyncFunctionDef)
                )
                and _shaped_name(member.name, settings)
            }
            shaped += len(methods)
    return shaped > len(items)