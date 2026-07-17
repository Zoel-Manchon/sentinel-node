import pytest

from node.adapters.security.hmac_signer import HmacSigner, HmacVerifier
from node.adapters.security.keyring import build_keyring, derive_key, revoke
from node.adapters.security.signed_codec import SignedCodec

MASTER = b"sentinel-master-secret-for-tests"
NODES = ["sentinel-01", "node-ml-01"]


class _FakeCodec:
    def encode(self, frame):
        return ("F:%s" % frame).encode("utf-8")

    def decode(self, payload):
        return payload.decode("utf-8")


def _node(node_id):
    return SignedCodec(_FakeCodec(), signer=HmacSigner(derive_key(MASTER, node_id), key_id=node_id))


def _gateway(keyring=None):
    return SignedCodec(_FakeCodec(), verifier=HmacVerifier(keyring or build_keyring(MASTER, NODES)))


def test_round_trip_signed_then_verified():
    signed = _node("sentinel-01").encode("hello")
    assert _gateway().decode(signed) == "F:hello"


def test_tampered_payload_is_rejected():
    signed = bytearray(_node("sentinel-01").encode("hello"))
    signed[-1] ^= 0x01
    with pytest.raises(ValueError):
        _gateway().decode(bytes(signed))


def test_unknown_or_revoked_key_is_rejected():
    signed = _node("sentinel-01").encode("x")
    ring = revoke(build_keyring(MASTER, NODES), "sentinel-01")
    with pytest.raises(ValueError):
        _gateway(ring).decode(signed)


def test_each_node_has_a_distinct_key():
    assert derive_key(MASTER, "sentinel-01") != derive_key(MASTER, "node-ml-01")
