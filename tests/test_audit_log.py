from node.adapters.security.audit_log import AuditLog


def test_empty_log_verifies():
    assert AuditLog().verify() is True


def test_chain_links_and_verifies():
    log = AuditLog()
    log.append({"kind": "anomaly", "device_id": "sentinel-01"})
    log.append({"kind": "node_offline", "device_id": "node-ml-01"})
    assert len(log) == 2
    assert log.verify() is True
    assert log.entries[1]["prev"] == log.entries[0]["hash"]


def test_tampering_is_detected():
    log = AuditLog()
    log.append({"kind": "anomaly", "device_id": "sentinel-01"})
    log.append({"kind": "auth_fail", "device_id": "intruder"})
    log._entries[0]["event"]["device_id"] = "spoofed"
    assert log.verify() is False
