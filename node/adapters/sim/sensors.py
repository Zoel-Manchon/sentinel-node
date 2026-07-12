"""Simulated adapters.

Sensors -> Measurements: SimBME680 (air), SimLD2410 (presence/distance).
Detectors -> Events:     SimAudioML (sound classes), SimVisionCam (person count).

Same names + measurement/channel names the hardware adapters will use, so the
sim->hw swap in the runner is mechanical.
"""

import random

from node.domain.model import (
    UNIT_BOOL,
    UNIT_CELSIUS,
    UNIT_COUNT,
    UNIT_HPA,
    UNIT_IAQ,
    UNIT_METER,
    UNIT_OHM,
    UNIT_PERCENT,
    Event,
    Measurement,
)
from node.domain.ports import DetectorPort, SensorError, SensorPort


class SimBME680(SensorPort):
    """Air: temperature / humidity / pressure / gas resistance / IAQ."""

    name = "bme680"

    def __init__(self, world, fail_rate: float = 0.0, seed: int = None):
        self._world = world
        self._fail_rate = fail_rate
        self._rng = random.Random(seed)

    def warmup_seconds(self) -> int:
        return 5  # gas heater needs to stabilize

    def read(self) -> list:
        if self._rng.random() < self._fail_rate:
            raise SensorError(self.name, "simulated I2C NAK")
        return [
            Measurement("temperature", self._world.temperature_c(), UNIT_CELSIUS),
            Measurement("humidity", self._world.humidity_pct(), UNIT_PERCENT),
            Measurement("pressure", self._world.pressure_hpa(), UNIT_HPA),
            Measurement("gas_resistance", self._world.gas_resistance_ohm(), UNIT_OHM),
            Measurement("iaq", self._world.iaq(), UNIT_IAQ),
        ]


class SimLD2410(SensorPort):
    """Presence radar: occupancy flag + distance to nearest target."""

    name = "ld2410"

    def __init__(self, world, fail_rate: float = 0.0, seed: int = None):
        self._world = world
        self._fail_rate = fail_rate
        self._rng = random.Random(seed)

    def read(self) -> list:
        if self._rng.random() < self._fail_rate:
            raise SensorError(self.name, "simulated UART timeout")
        dist = self._world.presence_distance_m()
        return [
            Measurement("presence", 1.0 if dist > 0 else 0.0, UNIT_BOOL),
            Measurement("target_distance", dist, UNIT_METER),
        ]


class SimAudioML(DetectorPort):
    """Edge acoustic classifier. Emits a sound-class Event + a level reading is
    handled separately; here we only classify. Raw audio never leaves."""

    channel = "audio"

    def __init__(self, world, seed: int = None):
        self._world = world
        self._rng = random.Random(seed)

    def detect(self) -> list:
        label, conf = self._world.sound_event()
        level = self._world.sound_level_dbfs()
        return [Event(self.channel, label, conf, meta={"level_dbfs": round(level, 1)})]


class SimVisionCam(DetectorPort):
    """Edge vision: person count + a REAL snapshot written to disk.

    Resolves the current scene to an image:
    - if an AI bank exists (tools/generate_bank.py), copies the matching bank
      image (realistic photo);
    - otherwise renders a Pillow placeholder (silhouettes) so the pipeline
      works with zero setup.

    The telemetry Event carries only the snapshot *path* — never the bytes.
    """

    channel = "vision"

    def __init__(self, world, seed: int = None, snapshot_dir: str = None,
                 bank_dir: str = None, write_images: bool = True):
        self._world = world
        self._rng = random.Random(seed)
        self._n = 0
        self._snapshot_dir = snapshot_dir or "docs/snapshots/cam-01"
        self._write_images = write_images
        self._bank = None
        if bank_dir:
            from node.adapters.vision.bank import ImageBank
            self._bank = ImageBank(bank_dir)

    def _write_snapshot(self, rel_path: str, count: int, anomaly: bool):
        import os
        import shutil
        abs_path = os.path.join(self._snapshot_dir, os.path.basename(rel_path))
        os.makedirs(self._snapshot_dir, exist_ok=True)
        # 1) AI bank if available
        if self._bank is not None:
            src = self._bank.resolve(count, anomaly)
            if src:
                shutil.copyfile(src, abs_path)
                return abs_path
        # 2) Pillow placeholder fallback
        from node.adapters.vision.placeholder import render_scene
        ts = str(self._world._clock.now())
        render_scene(abs_path, count, anomaly=anomaly, timestamp=ts,
                     seed=self._rng.randint(0, 1_000_000))
        return abs_path

    def detect(self) -> list:
        count = self._world.occupancy()
        anomaly = self._world.is_raining() if hasattr(self._world, "is_raining") else False
        label = "person" if count > 0 else "clear"
        conf = self._rng.uniform(0.75, 0.95) if count > 0 else self._rng.uniform(0.8, 0.98)
        meta = {"count": count}
        if count > 0:
            self._n += 1
            rel = "%06d.jpg" % self._n
            meta["snapshot"] = "snapshots/cam-01/%s" % rel
            if self._write_images:
                meta["snapshot_abs"] = self._write_snapshot(rel, count, anomaly)
        return [Event(self.channel, label, conf, meta=meta)]


class SimPowerMonitor:
    """Mains-backed node: near-constant with tiny ripple (not battery-critical
    like the weather station, but kept for pipeline symmetry)."""

    def __init__(self, world, voltage: float = 4.05):
        self._world = world
        self._v = voltage

    def battery_voltage(self) -> float:
        import random as _r
        return round(self._v + _r.uniform(-0.02, 0.02), 3)


class StaticSensor(SensorPort):
    def __init__(self, name: str, measurements: list):
        self.name = name
        self._measurements = measurements

    def read(self) -> list:
        return list(self._measurements)


class StaticDetector(DetectorPort):
    def __init__(self, channel: str, events: list):
        self.channel = channel
        self._events = events

    def detect(self) -> list:
        return list(self._events)


# silence unused import linters for re-exported units used in tests
_UNUSED = (UNIT_COUNT,)
