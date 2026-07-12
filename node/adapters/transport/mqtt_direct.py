"""MQTT transport — simulation-phase path (station publishes straight to the
broker; no LoRa hop yet).

Topic layout (Home Assistant / Node-RED friendly):
    iot/<device_id>/state        full JSON frame (retained)

With hardware, this adapter moves to the *gateway* (LoRa -> MQTT bridge) and
the station swaps to LoRaTransport. Same TransportPort either way.
"""

import json

from node.domain.ports import TransportPort


class MqttTransport(TransportPort):
    def __init__(self, host: str = "localhost", port: int = 1883,
                 base_topic: str = "iot", client=None):
        self._base = base_topic.rstrip("/")
        if client is not None:
            self._client = client  # injected in tests
        else:  # pragma: no cover — network wiring
            import paho.mqtt.client as mqtt

            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5
            )
            self._client.connect(host, port, keepalive=60)
            self._client.loop_start()

    def send(self, payload: bytes) -> None:
        device_id = json.loads(payload).get("device_id", "unknown")
        topic = "%s/%s/state" % (self._base, device_id)
        self._client.publish(topic, payload, qos=1, retain=True)

    def close(self) -> None:
        try:  # pragma: no cover
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass
