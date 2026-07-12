import pytest

from node.domain.model import (
    UNIT_CELSIUS,
    UNIT_METER,
    Event,
    Measurement,
    TelemetryFrame,
)


class TestMeasurement:
    def test_valid(self):
        m = Measurement("temperature", 21.5, UNIT_CELSIUS)
        assert m.value == 21.5

    def test_rejects_unknown_unit(self):
        with pytest.raises(ValueError):
            Measurement("x", 1.0, "kelvin")


class TestEvent:
    def test_valid(self):
        e = Event("audio", "glass_break", 0.92, {"level_dbfs": -8.0})
        assert e.label == "glass_break"
        assert e.meta["level_dbfs"] == -8.0

    def test_rejects_empty_channel(self):
        with pytest.raises(ValueError):
            Event("", "x")

    def test_rejects_bad_confidence(self):
        with pytest.raises(ValueError):
            Event("audio", "x", 1.5)

    def test_defaults(self):
        e = Event("vision", "clear")
        assert e.confidence == 1.0
        assert e.meta == {}


class TestTelemetryFrame:
    def _frame(self, **kw):
        d = dict(device_id="sentinel-01", timestamp=1_750_000_000,
                 measurements=[Measurement("target_distance", 2.5, UNIT_METER)],
                 events=[Event("audio", "quiet", 0.9)])
        d.update(kw)
        return TelemetryFrame(**d)

    def test_carries_both_kinds(self):
        f = self._frame()
        assert f.get("target_distance").value == 2.5
        assert f.events_on("audio")[0].label == "quiet"

    def test_to_dict_shape(self):
        d = self._frame(sequence=3).to_dict()
        assert d["seq"] == 3
        assert d["readings"]["target_distance"] == {"v": 2.5, "u": UNIT_METER}
        assert d["events"][0]["ch"] == "audio"

    def test_events_default_empty(self):
        f = TelemetryFrame("d", 1, [Measurement("target_distance", 1.0, UNIT_METER)])
        assert f.events == []
