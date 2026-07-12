# gateway — LoRa → MQTT bridge (optional, hardware phase)

The ambient + presence node (Node A) can report over LoRa P2P to save power;
this gateway would receive SX1276 frames, decode with the `CodecPort`
implementation, and republish to MQTT reusing `MqttTransport`.

The edge-ML node (Node B) is WiFi-native (it already needs WiFi/PSRAM for the
models), so it publishes to MQTT directly and skips the gateway.

Planned for the hardware phase — see the checklist in the root README.
