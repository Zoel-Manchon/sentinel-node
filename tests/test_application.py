import pytest

from node.adapters.codec.json_codec import JsonCodec
from node.adapters.sim.clock import ManualClock
from node.adapters.sim.sensors import StaticDetector, StaticSensor
from node.adapters.transport.console import MemoryTransport
from node.application.collect import CollectTelemetry, PublishTelemetry
from node.application.scheduler import DutyCycleScheduler
from node.domain.model import UNIT_METER, Event, Measurement, TelemetryFrame
from node.domain.ports import DetectorPort, SensorError, SensorPort


class BrokenSensor(SensorPort):
    name = "broken"

    def read(self):
        raise SensorError(self.name, "boom")


class BrokenDetector(DetectorPort):
    channel = "broken"

    def detect(self):
        raise RuntimeError("inference crashed")


def make_collector(sensors=None, detectors=None, power=None):
    sensors = sensors if sensors is not None else [
        StaticSensor("ld2410", [Measurement("target_distance", 2.5, UNIT_METER)]),
    ]
    detectors = detectors if detectors is not None else [
        StaticDetector("audio", [Event("audio", "quiet", 0.9)]),
    ]
    return CollectTelemetry("sentinel-test", sensors, ManualClock(1000),
                            detectors=detectors, power=power)


class TestCollectTelemetry:
    def test_needs_at_least_one_producer(self):
        with pytest.raises(ValueError):
            CollectTelemetry("x", [], ManualClock(), detectors=[])

    def test_collects_measurements_and_events(self):
        frame = make_collector().execute()
        assert frame.get("target_distance").value == 2.5
        assert frame.events_on("audio")[0].label == "quiet"

    def test_partial_frame_on_sensor_failure(self):
        good = StaticSensor("ld2410", [Measurement("target_distance", 1.0, UNIT_METER)])
        c = make_collector(sensors=[BrokenSensor(), good])
        frame = c.execute()
        assert frame.get("target_distance") is not None
        assert len(c.last_errors) == 1

    def test_detector_crash_does_not_kill_node(self):
        c = make_collector(detectors=[BrokenDetector()])
        frame = c.execute()  # sensor still produced data
        assert frame.get("target_distance") is not None
        assert len(c.last_errors) == 1

    def test_all_producers_failing_raises(self):
        c = make_collector(sensors=[BrokenSensor()], detectors=[BrokenDetector()])
        with pytest.raises(SensorError):
            c.execute()

    def test_sequence_increments(self):
        c = make_collector()
        assert c.execute().sequence == 0
        assert c.execute().sequence == 1


class TestPublishAndSchedule:
    def test_publish_roundtrip(self):
        t = MemoryTransport()
        f = PublishTelemetry(make_collector(), JsonCodec(), t).execute()
        assert JsonCodec().decode(t.payloads[0]).device_id == f.device_id

    def test_scheduler_runs_and_sleeps_between(self):
        clock = ManualClock(0)
        pub = PublishTelemetry(make_collector(), JsonCodec(), MemoryTransport())
        frames = []
        done = DutyCycleScheduler(pub, clock, 60).run(cycles=3, on_frame=frames.append)
        assert done == 3
        assert clock.sleep_calls == [60, 60]


class TestCodec:
    def test_roundtrip_with_events(self):
        frame = TelemetryFrame(
            "sentinel-01", 1_750_000_123,
            [Measurement("target_distance", 3.14159, UNIT_METER)],
            events=[Event("audio", "glass_break", 0.923, {"level_dbfs": -8.2}),
                    Event("vision", "person", 0.88, {"count": 2})],
            sequence=5)
        decoded = JsonCodec().decode(JsonCodec().encode(frame))
        assert decoded.get("target_distance").value == round(3.14159, 3)
        assert decoded.events_on("audio")[0].label == "glass_break"
        assert decoded.events_on("vision")[0].meta["count"] == 2

    def test_deterministic(self):
        c = JsonCodec()
        f = TelemetryFrame("d", 1, [Measurement("target_distance", 1.0, UNIT_METER)])
        assert c.encode(f) == c.encode(f)
