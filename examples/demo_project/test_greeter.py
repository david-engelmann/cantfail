from unittest.mock import Mock


def test_fetch_returns_what_it_was_told():
    client = Mock()
    client.fetch.return_value = 42
    result = client.fetch()
    assert result == 42
