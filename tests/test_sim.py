import pytest

from node.adapters.sim.clock import ManualClock
from node.adapters.sim.environment import SpaceWorld
from node.adapters.sim.sensors import (
    SimAudioML,
    SimBME680,
    SimLD2410,
    SimVisionCam,
)
from node.domain.ports import SensorError

NIGHT = 3 * 3600
MIDDAY = 11 * 3600


def world_at(seconds_of_day, seed=1):
    clock = ManualClock(seconds_of_day)
    return SpaceWorld(clock, seed=seed), clock


class TestSpaceWorld:
    def test_empty_at_night_occupied_midday(self):
        w, clock = world_at(NIGHT)
        assert w.occupancy() == 0
        assert not w.is_occupied()
        clock._now = MIDDAY
        assert w.occupancy() > 0

    def test_presence_distance_zero_when_empty(self):
        w, _ = world_at(NIGHT)
        assert w.presence_distance_m() == 0.0

    def test_presence_distance_in_range_when_occupied(self):
        w, _ = world_at(MIDDAY)
        d = w.presence_distance_m()
        assert d == 0.0 or 0.75 <= d <= 5.0

    def test_air_worse_when_occupied(self):
        w_night, _ = world_at(NIGHT)
        for _ in range(50):
            w_night._step()
        r_night = w_night.gas_resistance_ohm()

        w_day, clock = world_at(MIDDAY)
        for _ in range(200):
            clock.advance(60)
            w_day._step()
        r_day = w_day.gas_resistance_ohm()
        assert r_day < r_night  # lower resistance = worse air

    def test_iaq_bounds(self):
        w, clock = world_at(MIDDAY)
        for _ in range(100):
            clock.advance(60)
            assert 0.0 <= w.iaq() <= 500.0

    def test_forced_anomaly_surfaces_in_sound_event(self):
        w, _ = world_at(MIDDAY)
        w.force_anomaly("glass_break", 30)
        label, conf = w.sound_event()
        assert label == "glass_break"
        assert conf >= 0.8


class TestSimSensors:
    def test_bme680_five_measurements(self):
        w, _ = world_at(MIDDAY)
        names = {m.name for m in SimBME680(w).read()}
        assert names == {"temperature", "humidity", "pressure", "gas_resistance", "iaq"}

    def test_ld2410_presence_matches_distance(self):
        w, _ = world_at(NIGHT)
        by = {m.name: m.value for m in SimLD2410(w).read()}
        assert by["presence"] == 0.0
        assert by["target_distance"] == 0.0

    def test_fail_rate_one_raises(self):
        w, _ = world_at(MIDDAY)
        with pytest.raises(SensorError):
            SimBME680(w, fail_rate=1.0).read()


class TestSimDetectors:
    def test_audio_emits_event_with_level(self):
        w, _ = world_at(MIDDAY)
        (ev,) = SimAudioML(w).detect()
        assert ev.channel == "audio"
        assert "level_dbfs" in ev.meta

    def test_vision_clear_when_empty(self):
        w, _ = world_at(NIGHT)
        (ev,) = SimVisionCam(w).detect()
        assert ev.label == "clear"
        assert ev.meta["count"] == 0
        assert "snapshot" not in ev.meta  # no image ref when nobody's there

    def test_vision_person_carries_snapshot_ref_not_blob(self, tmp_path):
        w, _ = world_at(MIDDAY)
        cam = SimVisionCam(w, snapshot_dir=str(tmp_path))
        # keep trying until an occupied read (occupancy has noise)
        ev = None
        for _ in range(20):
            (ev,) = cam.detect()
            if ev.label == "person":
                break
        if ev.label == "person":
            assert ev.meta["snapshot"].endswith(".jpg")
            assert isinstance(ev.meta["snapshot"], str)  # a path, never bytes
            # a real image file was written to disk
            import os
            assert os.path.isfile(ev.meta["snapshot_abs"])
            assert os.path.getsize(ev.meta["snapshot_abs"]) > 0

    def test_vision_no_snapshots_flag_skips_file(self, tmp_path):
        w, _ = world_at(MIDDAY)
        cam = SimVisionCam(w, snapshot_dir=str(tmp_path), write_images=False)
        for _ in range(20):
            (ev,) = cam.detect()
            if ev.label == "person":
                assert "snapshot" in ev.meta        # path still present
                assert "snapshot_abs" not in ev.meta  # but no file written
                break
