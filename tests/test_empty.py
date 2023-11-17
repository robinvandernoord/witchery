from src.witchery import Empty


class HasEmpty:
    empty = Empty()


def test_empty():
    empty = Empty()
    assert not empty
    assert not empty.property
    assert not empty["item"]

    assert not HasEmpty().empty
    assert not (HasEmpty().empty is empty)

    lst = [1, 2, 3]
    assert empty + lst is lst

    assert not str(empty)
    assert not repr(empty)

    for i, x in enumerate(empty):
        assert not x
        assert not i

    assert not empty()

    assert not empty.some['nested']().things

