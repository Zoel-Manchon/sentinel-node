"""Ports — the hexagon's edges. Plain base classes (no abc; MicroPython-safe).

Two driving families:
- SensorPort:   produces scalar Measurements (BME680, LD2410 distance...).
- DetectorPort: runs an edge model, produces discrete Events (audio, vision).

Driven: CodecPort, TransportPort. Support: ClockPort, PowerMonitorPort.
"""


class SensorPort:
    """Produces a list of Measurement objects."""

    name = "sensor"

    def read(self) -> list:
        raise NotImplementedError

    def warmup_seconds(self) -> int:
        return 0


class DetectorPort:
    """Runs an edge classifier and returns a list of Event objects.

    The heavy lifting (TinyML inference, frame diff) happens INSIDE the adapter,
    on the device. The port only ever hands back verdicts — never raw media.
    """

    channel = "detector"

    def detect(self) -> list:
        raise NotImplementedError


class PowerMonitorPort:
    def battery_voltage(self) -> float:
        raise NotImplementedError


class ClockPort:
    def now(self) -> int:
        raise NotImplementedError

    def sleep(self, seconds: float) -> None:
        raise NotImplementedError


class CodecPort:
    def encode(self, frame) -> bytes:
        raise NotImplementedError

    def decode(self, payload: bytes):
        raise NotImplementedError


class TransportPort:
    def send(self, payload: bytes) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class SensorError(Exception):
    def __init__(self, sensor_name: str, detail: str = ""):
        self.sensor_name = sensor_name
        self.detail = detail
        super().__init__("%s: %s" % (sensor_name, detail))
