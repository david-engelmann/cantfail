"""Read the collection naming settings of an analysed project.

Slice 4 retires the limit E7 stated. The selector and discovery
read the three naming settings pytest itself reads, which are
python_functions and python_classes and python_files, from the
one config source pytest would use for the project. The sources
are tried in the order F1 states, which is the order pytest 9
searches them in, and only the winning source contributes
settings. An absent setting means its default is in force, which
the rest of the tool reads as the rules the earlier slices always
used.
"""

from __future__ import annotations

import configparser
import fnmatch
import tomllib
from dataclasses import dataclass
from pathlib import Path

_KEYS = ("python_functions", "python_classes", "python_files")

_DEFAULT_PATTERNS = {
    "python_functions": ("test",),
    "python_classes": ("Test",),
    "python_files": ("test_*.py", "*_test.py"),
}


@dataclass(frozen=True)
class CollectionSettings:
    """The naming settings in force for one analysed project.

    Each field is the tuple of patterns a settings source gave, or
    None when no setting is in force and the default applies.
    """

    python_functions: tuple[str, ...] | None = None
    python_classes: tuple[str, ...] | None = None
    python_files: tuple[str, ...] | None = None

    def non_defaults(self) -> dict[str, list[str]]:
        """The settings in force whose patterns differ from the
        pytest defaults, in a fixed key order, for the report
        disclosure of F5. A setting restated at exactly its
        default value is not a difference and is not named."""
        found: dict[str, list[str]] = {}
        for key in _KEYS:
            value = getattr(self, key)
            if value is not None and tuple(value) != _DEFAULT_PATTERNS[key]:
                found[key] = list(value)
        return found


DEFAULT_SETTINGS = CollectionSettings()


def name_matches(name: str, patterns: tuple[str, ...]) -> bool:
    """Return True when a function or class name matches a
    pattern, in the pytest sense of F2. A name matches when it
    starts with the pattern or matches the pattern as a glob."""
    return any(
        name.startswith(pattern) or fnmatch.fnmatchcase(name, pattern)
        for pattern in patterns
    )


def file_matches(
    relative: str, filename: str, patterns: tuple[str, ...]
) -> bool:
    """Return True when a file matches a python_files pattern, in
    the pytest sense of F2. A pattern holding no path separator
    matches the file name alone as a glob. A pattern holding a
    separator matches the project relative path as a glob."""
    for pattern in patterns:
        if "/" in pattern:
            if fnmatch.fnmatchcase(relative, pattern):
                return True
        elif fnmatch.fnmatchcase(filename, pattern):
            return True
    return False


def _split_words(value) -> tuple[str, ...]:
    """Read one setting value as a tuple of patterns.

    A string splits on whitespace, the ini reading. A list keeps
    its items as strings, the native TOML reading. Any other
    scalar becomes its string form, the conversion pytest itself
    applies to scalar values in an ini mode table, so a malformed
    project yields patterns rather than a crash.
    """
    if isinstance(value, str):
        return tuple(value.split())
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return (str(value),)


def _settings_from_table(table: dict) -> CollectionSettings:
    found = {}
    for key in _KEYS:
        if key in table:
            found[key] = _split_words(table[key])
    return CollectionSettings(**found)


def _read_ini(path: Path) -> configparser.ConfigParser | None:
    """Parse an ini style file, or return None when the file
    cannot be parsed at all."""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(path, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError, OSError):
        return None
    return parser


def _settings_from_parser(
    parser: configparser.ConfigParser, section: str
) -> CollectionSettings:
    found = {}
    for key in _KEYS:
        if parser.has_option(section, key):
            found[key] = tuple(parser.get(section, key).split())
    return CollectionSettings(**found)


def _ini_source(
    path: Path, section: str, always: bool = False
) -> CollectionSettings | None:
    """Settings from an ini style source, or None when the file
    carries no pytest section and so is not a source at all.

    A file that cannot be parsed is a source that contributes
    nothing, under the broken source rule of F1, so it returns the
    defaults rather than None. A file named as always a source
    contributes the defaults when its section is absent, the way
    pytest treats its own ini files.
    """
    parser = _read_ini(path)
    if parser is None:
        return CollectionSettings()
    if not parser.has_section(section):
        return CollectionSettings() if always else None
    return _settings_from_parser(parser, section)


def _load_toml(path: Path) -> dict | None:
    """Parse a TOML file, or return None when it cannot be read
    as a table at all."""
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _pytest_toml_source(path: Path) -> CollectionSettings:
    """Settings from a pytest.toml style file.

    The file is always a source when it exists. Its pytest table
    holds the settings under their own names. A file that cannot
    be parsed, or whose pytest value is not a table, is a broken
    source and contributes nothing.
    """
    data = _load_toml(path)
    if data is None:
        return CollectionSettings()
    table = data.get("pytest", {})
    if not isinstance(table, dict):
        return CollectionSettings()
    return _settings_from_table(table)


def _pyproject_source(path: Path) -> CollectionSettings | None:
    """Settings from a pyproject.toml file, or None when the file
    carries no pytest table and so is not a source at all.

    The pytest table may hold the naming settings directly, in
    native TOML form, or under an ini_options table, in string
    form, and holding both at once is a broken source because
    pytest refuses that file. A table of the wrong shape is a
    broken source too. A broken source contributes nothing and
    blocks later sources, under the rule of F1.
    """
    data = _load_toml(path)
    if data is None:
        return CollectionSettings()
    tool = data.get("tool")
    if tool is not None and not isinstance(tool, dict):
        return CollectionSettings()
    if not isinstance(tool, dict) or "pytest" not in tool:
        return None
    table = tool["pytest"]
    if not isinstance(table, dict):
        return CollectionSettings()
    native = {k: v for k, v in table.items() if k != "ini_options"}
    ini_options = table.get("ini_options")
    if native and ini_options is not None:
        return CollectionSettings()
    if native:
        return _settings_from_table(native)
    if ini_options is not None:
        if not isinstance(ini_options, dict):
            return CollectionSettings()
        return _settings_from_table(ini_options)
    return None


def load_collection_settings(project: Path) -> CollectionSettings:
    """Read the naming settings in force for one project root.

    The first source in the order F1 states wins and only that
    source contributes. A project with no source is read with the
    defaults in force.
    """
    for name in ("pytest.toml", ".pytest.toml"):
        candidate = project / name
        if candidate.is_file():
            return _pytest_toml_source(candidate)
    for name in ("pytest.ini", ".pytest.ini"):
        candidate = project / name
        if candidate.is_file():
            settings = _ini_source(candidate, "pytest", always=True)
            if settings is not None:
                return settings
    pyproject = project / "pyproject.toml"
    if pyproject.is_file():
        settings = _pyproject_source(pyproject)
        if settings is not None:
            return settings
    tox_ini = project / "tox.ini"
    if tox_ini.is_file():
        settings = _ini_source(tox_ini, "pytest")
        if settings is not None:
            return settings
    setup_cfg = project / "setup.cfg"
    if setup_cfg.is_file():
        settings = _ini_source(setup_cfg, "tool:pytest")
        if settings is not None:
            return settings
    return CollectionSettings()
