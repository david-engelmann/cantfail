"""Synthetic fixture projects used by the cantfail tests.

Every project here is invented for this repository. No fixture is
drawn from a real codebase.
"""

from __future__ import annotations

from pathlib import Path


def write_project(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    return root


WELL_TESTED = {
    "calc.py": (
        "def add_one(x):\n"
        "    return x + 1\n"
        "\n"
        "\n"
        "def is_adult(age):\n"
        "    return age >= 18\n"
        "\n"
        "\n"
        "def enabled():\n"
        "    return True\n"
    ),
    "test_calc.py": (
        "from calc import add_one, enabled, is_adult\n"
        "\n"
        "\n"
        "def test_add_one():\n"
        "    assert add_one(1) == 2\n"
        "    assert add_one(0) == 1\n"
        "\n"
        "\n"
        "def test_is_adult_boundary():\n"
        "    assert is_adult(18) is True\n"
        "    assert is_adult(17) is False\n"
        "\n"
        "\n"
        "def test_enabled():\n"
        "    assert enabled() is True\n"
    ),
}


DECORATIVE = {
    "greeter.py": (
        "def greet():\n"
        "    return 'hello'\n"
    ),
    "test_greeter.py": (
        "from unittest.mock import Mock\n"
        "\n"
        "\n"
        "def test_fetch_returns_what_it_was_told():\n"
        "    client = Mock()\n"
        "    client.fetch.return_value = 42\n"
        "    result = client.fetch()\n"
        "    assert result == 42\n"
    ),
}


BASELINE_FAILING = {
    "broken.py": (
        "def value():\n"
        "    return 1\n"
    ),
    "test_broken.py": (
        "from broken import value\n"
        "\n"
        "\n"
        "def test_value():\n"
        "    assert value() == 2\n"
    ),
}


UNMATCHED_STEM = {
    "thing.py": (
        "def value():\n"
        "    return 5\n"
    ),
    "test_misc.py": (
        "from thing import value\n"
        "\n"
        "\n"
        "def test_value():\n"
        "    assert value() == 5\n"
    ),
}
