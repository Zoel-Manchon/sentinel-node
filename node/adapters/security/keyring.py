"""Per-node HMAC keyring — derive, rotate and revoke node keys.

Each node's key is derived from one master via HMAC-SHA256; key_id == node-id
== mTLS cert CN. Revoke a node by dropping its key_id from the verifier keyring.
"""
import hashlib
import hmac


def derive_key(master: bytes, node_id: str) -> bytes:
    if not master:
        raise ValueError("master secret must not be empty")
    return hmac.new(master, node_id.encode("utf-8"), hashlib.sha256).digest()


def build_keyring(master: bytes, node_ids) -> dict:
    return {node_id: derive_key(master, node_id) for node_id in node_ids}


def rotate(master: bytes, node_id: str, version: int):
    key_id = "%s.v%d" % (node_id, version)
    return key_id, derive_key(master, key_id)


def revoke(keyring: dict, key_id: str) -> dict:
    return {k: v for k, v in keyring.items() if k != key_id}
