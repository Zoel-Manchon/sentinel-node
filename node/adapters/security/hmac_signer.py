"""Keyed MAC over the encoded frame bytes — payload integrity.

A spoofed MQTT publish can't inject fake occupancy/anomaly events without the
per-node key. Sign on the node, verify on the gateway. The envelope is
`key_id|hexmac|<payload-bytes>`; verification is constant-time.
"""
import hashlib
import hmac

_SEP = b"|"


class HmacSigner:
    def __init__(self, key: bytes, key_id: str = "k1"):
        if not key:
            raise ValueError("key must not be empty")
        self._key = key
        self.key_id = key_id

    def sign(self, payload: bytes) -> bytes:
        mac = hmac.new(self._key, payload, hashlib.sha256).hexdigest()
        return ("%s|%s|" % (self.key_id, mac)).encode("ascii") + payload


class HmacVerifier:
    def __init__(self, keyring: dict):
        self._keyring = dict(keyring)

    def verify(self, signed: bytes):
        """Return the inner payload if the MAC is valid, else None."""
        try:
            key_id, mac_hex, payload = signed.split(_SEP, 2)
        except ValueError:
            return None
        key = self._keyring.get(key_id.decode("ascii", "ignore"))
        if key is None:
            return None
        expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, mac_hex.decode("ascii", "ignore")):
            return None
        return payload
