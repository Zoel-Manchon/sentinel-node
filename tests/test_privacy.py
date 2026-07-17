"""Privacy-by-design invariant: raw media never enters an Event.

The whole project pledges that images/audio stay on the device and only the
verdict travels. This enforces it in CI: an Event refuses any binary payload.
"""
import pytest

from node.domain.model import Event


def test_event_accepts_scalar_meta():
    e = Event("vision", "person", 0.9, meta={"count": 1, "snapshot": "/img/1.jpg"})
    assert e.meta["count"] == 1


def test_event_rejects_raw_bytes_in_meta():
    with pytest.raises(ValueError):
        Event("audio", "glass_break", 0.9, meta={"clip": b"\x00\x01raw-audio"})


def test_event_rejects_bytearray_in_meta():
    with pytest.raises(ValueError):
        Event("vision", "person", 0.8, meta={"jpeg": bytearray(b"\xff\xd8\xff")})
