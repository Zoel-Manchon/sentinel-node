"""MQTT over TLS/mTLS transport (TransportPort). No core change: TLS lives here.

Each node presents its client cert; the broker rejects unknown clients. Mirrors
MqttTransport but connects to the 8883 TLS listener.
"""
import ssl

import paho.mqtt.client as mqtt


class MqttTlsTransport:
    def __init__(self, host, port=8883, topic="sentinel/telemetry",
                 ca_certs="ca.crt", certfile=None, keyfile=None):
        self._topic = topic
        self._client = mqtt.Client()
        self._client.tls_set(ca_certs=ca_certs, certfile=certfile, keyfile=keyfile,
                             tls_version=ssl.PROTOCOL_TLSv1_2)
        self._client.tls_insecure_set(False)
        self._client.connect(host, port)
        self._client.loop_start()

    def send(self, payload: bytes) -> None:
        self._client.publish(self._topic, payload)
