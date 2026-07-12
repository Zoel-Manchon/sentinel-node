"""JSON codec — simulation-phase wire format.

Carries both scalar readings and discrete events. Compact separators, sorted
keys, values rounded: deterministic payloads for MQTT/Node-RED/InfluxDB.

For the LoRa hardware phase, a binary codec (struct-packed) would replace this
behind the same CodecPort — but note events with string labels don't compress
as cleanly as scalars, so the presence/air nodes are the LoRa-friendly ones;
audio/vision nodes are WiFi-native anyway.
"""

import json

from node.domain.model import Event, Measurement, TelemetryFrame
from node.domain.ports import CodecPort


class JsonCodec(CodecPort):
    def encode(self, frame: TelemetryFrame) -> bytes:
        doc = frame.to_dict()
        for reading in doc["readings"].values():
            reading["v"] = round(reading["v"], 3)
        for ev in doc["events"]:
            ev["conf"] = round(ev["conf"], 3)
        return json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def decode(self, payload: bytes) -> TelemetryFrame:
        doc = json.loads(payload.decode("utf-8"))
        measurements = [
            Measurement(name, r["v"], r["u"]) for name, r in sorted(doc["readings"].items())
        ]
        events = [
            Event(e["ch"], e["label"], e.get("conf", 1.0), e.get("meta"))
            for e in doc.get("events", [])
        ]
        return TelemetryFrame(
            device_id=doc["device_id"],
            timestamp=doc["ts"],
            measurements=measurements,
            events=events,
            sequence=doc.get("seq", 0),
        )
