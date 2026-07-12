"""Domain model — pure business objects.

MicroPython-compatible: no typing/dataclasses/enum/abc imports.

Two kinds of observation, on purpose:
- Measurement: a scalar physical reading (temperature, VOC, distance...).
- Event: a discrete classification/detection ("sound=glass_break conf=0.92",
  "vision: 1 person"). Events carry a label + confidence + optional metadata,
  NOT a blob. Images and raw audio never enter the telemetry frame — a
  time-series pipeline is not an object store. The camera/audio adapters run
  the model at the edge and emit the *verdict* as an Event.

Both ride in the same TelemetryFrame and flow through the same pipeline.
"""

# --- Units ------------------------------------------------------------------
UNIT_CELSIUS = "degC"
UNIT_HPA = "hPa"
UNIT_PERCENT = "%"
UNIT_OHM = "ohm"
UNIT_IAQ = "iaq"
UNIT_METER = "m"
UNIT_BOOL = "bool"
UNIT_VOLT = "V"
UNIT_COUNT = "count"
UNIT_DBFS = "dBFS"
UNIT_RATIO = "ratio"

VALID_UNITS = (
    UNIT_CELSIUS, UNIT_HPA, UNIT_PERCENT, UNIT_OHM, UNIT_IAQ, UNIT_METER,
    UNIT_BOOL, UNIT_VOLT, UNIT_COUNT, UNIT_DBFS, UNIT_RATIO,
)


class Measurement:
    """A single scalar physical quantity."""

    __slots__ = ("name", "value", "unit")

    def __init__(self, name: str, value: float, unit: str):
        if not name:
            raise ValueError("measurement name must not be empty")
        if unit not in VALID_UNITS:
            raise ValueError("unknown unit: %s" % unit)
        self.name = name
        self.value = float(value)
        self.unit = unit

    def __repr__(self):
        return "Measurement(%s=%.3f %s)" % (self.name, self.value, self.unit)

    def __eq__(self, other):
        return (isinstance(other, Measurement) and self.name == other.name
                and self.value == other.value and self.unit == other.unit)


class Event:
    """A discrete detection/classification emitted by an edge model.

    `label` is the class ("glass_break", "person", "clear"); `confidence` in
    [0,1]; `meta` a small dict of scalars (distance, count, ref to an out-of-
    band artifact like an image path). No binary payloads here — ever.
    """

    __slots__ = ("channel", "label", "confidence", "meta")

    def __init__(self, channel: str, label: str, confidence: float = 1.0, meta: dict = None):
        if not channel:
            raise ValueError("event channel must not be empty")
        if not label:
            raise ValueError("event label must not be empty")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
        self.channel = channel
        self.label = label
        self.confidence = float(confidence)
        self.meta = dict(meta) if meta else {}

    def __repr__(self):
        return "Event(%s: %s @%.2f)" % (self.channel, self.label, self.confidence)

    def __eq__(self, other):
        return (isinstance(other, Event) and self.channel == other.channel
                and self.label == other.label and self.confidence == other.confidence)


class TelemetryFrame:
    """One report: scalar measurements + discrete events, one MQTT packet."""

    __slots__ = ("device_id", "timestamp", "measurements", "events", "sequence")

    def __init__(self, device_id: str, timestamp: int, measurements: list,
                 events: list = None, sequence: int = 0):
        if not device_id:
            raise ValueError("device_id must not be empty")
        if timestamp < 0:
            raise ValueError("timestamp must be a positive epoch value")
        if sequence < 0:
            raise ValueError("sequence must be >= 0")
        self.device_id = device_id
        self.timestamp = int(timestamp)
        self.measurements = list(measurements)
        self.events = list(events) if events else []
        self.sequence = int(sequence)

    def get(self, name: str):
        for m in self.measurements:
            if m.name == name:
                return m
        return None

    def events_on(self, channel: str) -> list:
        return [e for e in self.events if e.channel == channel]

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "ts": self.timestamp,
            "seq": self.sequence,
            "readings": {m.name: {"v": m.value, "u": m.unit} for m in self.measurements},
            "events": [
                {"ch": e.channel, "label": e.label, "conf": e.confidence, "meta": e.meta}
                for e in self.events
            ],
        }

    def __repr__(self):
        return "TelemetryFrame(%s seq=%d m=%d e=%d)" % (
            self.device_id, self.sequence, len(self.measurements), len(self.events))
