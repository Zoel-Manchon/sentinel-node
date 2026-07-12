"""Fitness functions: the hexagon stays a hexagon, or CI goes red."""

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORBIDDEN_IN_CORE = {"paho", "json", "machine", "requests", "typing",
                     "dataclasses", "abc", "enum", "asyncio"}
CORE_DIRS = ("node/domain", "node/application")


def imports_of(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def core_files():
    for d in CORE_DIRS:
        yield from (ROOT / d).glob("*.py")


class TestHexagonRules:
    def test_core_never_imports_adapters_or_infra(self):
        for path in core_files():
            for name in imports_of(path):
                assert name not in FORBIDDEN_IN_CORE, "%s imports %s" % (path.name, name)
                assert "adapters" not in name, "%s imports adapters" % path.name

    def test_core_is_micropython_friendly(self):
        for path in core_files():
            names = set(imports_of(path))
            assert "dataclasses" not in names
            assert "typing" not in names


class TestRunnerSmoke:
    def test_all_sensors_console(self, capsys):
        from runner.run_sim import main
        rc = main(["--cycles", "3", "--speed", "10000", "--seed", "7"])
        assert rc == 0
        out = capsys.readouterr().out.strip().splitlines()
        assert len(out) == 3
        assert '"device_id":"sentinel-01"' in out[0]

    def test_disable_flags(self, capsys):
        from runner.run_sim import main
        rc = main(["--cycles", "1", "--speed", "10000", "--seed", "7",
                   "--no-vision", "--no-audio"])
        assert rc == 0
        out = capsys.readouterr().out.strip()
        assert '"events":[]' in out  # detectors disabled -> no events

    def test_anomaly_cue_fires(self, capsys):
        from runner.run_sim import main
        rc = main(["--cycles", "3", "--speed", "100000", "--seed", "7",
                   "--anomaly-at", "0", "--anomaly-label", "glass_break"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "glass_break" in out


class TestMqttTopic:
    def test_publishes_to_iot_device_topic(self):
        from node.adapters.transport.mqtt_direct import MqttTransport
        published = []

        class FakeClient:
            def publish(self, topic, payload, qos=0, retain=False):
                published.append(topic)

        MqttTransport(client=FakeClient()).send(
            b'{"device_id":"sentinel-01","ts":1,"seq":0,"readings":{},"events":[]}')
        assert published[0] == "iot/sentinel-01/state"


class TestHwStubsAreHonest:
    def test_hw_sensor_fails_until_implemented(self):
        import pytest

        from node.adapters.hw.sensors import HwBME680
        from node.domain.ports import SensorError
        with pytest.raises(SensorError):
            HwBME680(i2c=None).read()
