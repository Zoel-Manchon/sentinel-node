"""Use cases — depend only on ports. No mqtt/json/machine here."""

from node.domain.model import UNIT_VOLT, Measurement, TelemetryFrame
from node.domain.ports import SensorError


class CollectTelemetry:
    """Reads all sensors + runs all detectors -> one TelemetryFrame.

    Sensors contribute Measurements; detectors contribute Events. A failing
    sensor is skipped (partial frame). A failing detector is skipped too — a
    missed inference must never take the node down.
    """

    def __init__(self, device_id: str, sensors: list, clock,
                 detectors: list = None, power=None):
        if not sensors and not detectors:
            raise ValueError("at least one sensor or detector is required")
        self._device_id = device_id
        self._sensors = list(sensors or [])
        self._detectors = list(detectors or [])
        self._clock = clock
        self._power = power
        self._sequence = 0

    def execute(self) -> TelemetryFrame:
        measurements = []
        events = []
        self.last_errors = []

        for sensor in self._sensors:
            try:
                measurements.extend(sensor.read())
            except SensorError as exc:
                self.last_errors.append(exc)

        for detector in self._detectors:
            try:
                events.extend(detector.detect())
            except Exception as exc:  # noqa: BLE001 — inference must not crash the node
                self.last_errors.append(exc)

        if self._power is not None:
            measurements.append(
                Measurement("battery_voltage", self._power.battery_voltage(), UNIT_VOLT))

        if not measurements and not events:
            raise SensorError("all", "no sensor or detector produced data")

        frame = TelemetryFrame(
            device_id=self._device_id,
            timestamp=self._clock.now(),
            measurements=measurements,
            events=events,
            sequence=self._sequence,
        )
        self._sequence += 1
        return frame


class PublishTelemetry:
    def __init__(self, collector: CollectTelemetry, codec, transport):
        self._collector = collector
        self._codec = codec
        self._transport = transport

    def execute(self) -> TelemetryFrame:
        frame = self._collector.execute()
        self._transport.send(self._codec.encode(frame))
        return frame
