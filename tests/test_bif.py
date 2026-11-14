import pytest

from arc.bif import BIF, make


def test_frames_by_time():
    b = BIF(make([b"one", b"two", b"three"], interval_ms=10000))
    assert len(b) == 3
    assert b.index_at(0) == 0 and b.index_at(9999) == 0
    assert b.index_at(10000) == 1 and b.index_at(99999) == 2
    assert b.frame(1) == b"two" and b.frame(3) is None


def test_not_a_bif():
    with pytest.raises(ValueError):
        BIF(b"nope" * 20)
