from calc import add_one, enabled, is_adult


def test_add_one():
    assert add_one(1) == 2
    assert add_one(0) == 1


def test_is_adult_boundary():
    assert is_adult(18) is True
    assert is_adult(17) is False


def test_enabled():
    assert enabled() is True
