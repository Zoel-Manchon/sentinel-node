"""Hardware adapters — SKELETONS, ready to fill when hardware arrives.

Same name/channel + measurement names as the sim adapters, so the swap in
runner/run_sim.py is mechanical. See WIRING.md for buses, drivers, pinout.
"""

from node.domain.model import Event, Measurement  # noqa: F401 — used when implemented
from node.domain.ports import DetectorPort, PowerMonitorPort, SensorError, SensorPort


class HwBME680(SensorPort):
    """I2C @ 0x76/0x77. Driver: BSEC (IAQ) or robert-hh/BME680 for raw gas."""

    name = "bme680"

    def __init__(self, i2c, address: int = 0x76):
        self._i2c = i2c
        self._address = address

    def warmup_seconds(self) -> int:
        return 5

    def read(self) -> list:
        raise SensorError(self.name, "hardware adapter not implemented yet")
        # TODO(hw): read T/H/P + gas_resistance; IAQ via BSEC or heuristic.


class HwLD2410(SensorPort):
    """UART 256000 8N1. Frames 0xF4F3F2F1 ... 0xF8F7F6F5. Distance per gate.
    GPIO OUT pin gives a simple presence bit; UART gives distance + energy."""

    name = "ld2410"

    def __init__(self, uart, out_pin=None):
        self._uart = uart
        self._out = out_pin

    def read(self) -> list:
        raise SensorError(self.name, "hardware adapter not implemented yet")
        # TODO(hw): parse target frame -> presence bit + target_distance (m).


class HwAudioML(DetectorPort):
    """ESP32-S3 + INMP441 (I2S, 24-bit). Runs a TinyML classifier on-device;
    emits only the winning class + confidence. Raw audio never leaves."""

    channel = "audio"

    def __init__(self, i2s, model=None):
        self._i2s = i2s
        self._model = model

    def detect(self) -> list:
        raise SensorError(self.channel, "hardware detector not implemented yet")
        # TODO(hw): capture window -> features (MFCC) -> model.infer -> Event.


class HwVisionCam(DetectorPort):
    """ESP32-CAM (OV2640). Runs person detection / frame diff on-device; emits
    an Event with count + a snapshot path saved out-of-band (SD/HTTP), not the
    JPEG. Publishing the image is a SEPARATE channel, never the telemetry frame."""

    channel = "vision"

    def __init__(self, camera, storage=None):
        self._camera = camera
        self._storage = storage

    def detect(self) -> list:
        raise SensorError(self.channel, "hardware detector not implemented yet")
        # TODO(hw): capture -> detect -> save snapshot -> Event(count, ref).


class HwPowerMonitor(PowerMonitorPort):
    def __init__(self, adc, divider_ratio: float = 2.0):
        self._adc = adc
        self._ratio = divider_ratio

    def battery_voltage(self) -> float:
        raise NotImplementedError("hardware adapter not implemented yet")
