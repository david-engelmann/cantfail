"""Pins for the Round 12 post-hoc verification repair.

The descent covers the synchronous statement forms. A fixture
standing under a top level async for or a top level async with
is not read, and those forms cannot stand in a module a run can
import, so no run registers such a fixture either. The pins
below hold that reading against a build that descends the
async forms.

Every fixture here is synthetic and written for this test
file.
"""

from cantfail.static_scan import scan_source

HEAD = "import pytest\nfrom unittest.mock import Mock\n\n"


def _return_fixture(indent, value):
    pad = " " * indent
    return (
        f"{pad}@pytest.fixture\n"
        f"{pad}def client():\n"
        f"{pad}    made = Mock()\n"
        f"{pad}    made.fetch.return_value = {value}\n"
        f"{pad}    return made\n"
    )


def _fetch_test(value):
    return (
        "def test_fetch(client):\n"
        f"    assert client.fetch() == {value}\n"
    )


def test_a_fixture_under_a_top_level_async_for_is_not_read():
    source = (
        HEAD
        + "async for _ in stream:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    assert scan_source(source, "test_client.py") == []


def test_a_fixture_under_a_top_level_async_with_is_not_read():
    source = (
        HEAD
        + "async with manager:\n"
        + _return_fixture(4, 42)
        + "\n"
        + _fetch_test(42)
    )
    assert scan_source(source, "test_client.py") == []


def test_the_async_forms_are_refused_at_compilation():
    import pytest

    for source in (
        "async for _ in stream:\n    pass\n",
        "async with manager:\n    pass\n",
    ):
        with pytest.raises(SyntaxError):
            compile(source, "probe.py", "exec")
