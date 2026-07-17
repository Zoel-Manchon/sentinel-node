"""CodecPort decorator that adds a keyed MAC over the encoded bytes.

Node side signs (encode); gateway side verifies (decode). No core change —
integrity lives entirely in this adapter, exactly where the roadmap wants it.
"""


class SignedCodec:
    def __init__(self, inner, signer=None, verifier=None):
        self._inner = inner
        self._signer = signer
        self._verifier = verifier

    def encode(self, frame) -> bytes:
        if self._signer is None:
            raise RuntimeError("SignedCodec.encode needs a signer")
        return self._signer.sign(self._inner.encode(frame))

    def decode(self, payload: bytes):
        if self._verifier is None:
            raise RuntimeError("SignedCodec.decode needs a verifier")
        inner = self._verifier.verify(payload)
        if inner is None:
            raise ValueError("bad_signature: payload failed HMAC verification")
        return self._inner.decode(inner)
