"""Console transport — zero-dependency smoke-test sink."""

from node.domain.ports import TransportPort


class ConsoleTransport(TransportPort):
    def __init__(self, writer=None):
        self._writer = writer or (lambda line: print(line, flush=True))
        self.sent_count = 0

    def send(self, payload: bytes) -> None:
        self._writer(payload.decode("utf-8", "replace"))
        self.sent_count += 1


class MemoryTransport(TransportPort):
    """Test double: keeps every payload."""

    def __init__(self):
        self.payloads = []

    def send(self, payload: bytes) -> None:
        self.payloads.append(payload)
