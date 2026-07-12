import os

from node.adapters.vision.bank import ImageBank, scene_for
from node.adapters.vision.placeholder import render_scene


class TestSceneResolution:
    def test_scene_for_counts(self):
        assert scene_for(0) == "empty"
        assert scene_for(1) == "one"
        assert scene_for(2) == "two"
        assert scene_for(5) == "three"

    def test_anomaly_overrides_count(self):
        assert scene_for(2, anomaly=True) == "anomaly"


class TestImageBank:
    def test_missing_bank_resolves_none(self, tmp_path):
        bank = ImageBank(str(tmp_path))
        assert not bank.is_complete()
        assert bank.resolve(2) is None

    def test_complete_bank_resolves_path(self, tmp_path):
        for scene in ("empty", "one", "two", "three", "anomaly"):
            (tmp_path / ("%s.jpg" % scene)).write_bytes(b"\xff\xd8\xff")  # tiny JPEG magic
        bank = ImageBank(str(tmp_path))
        assert bank.is_complete()
        assert bank.resolve(2).endswith("two.jpg")
        assert bank.resolve(0, anomaly=True).endswith("anomaly.jpg")


class TestPlaceholder:
    def test_renders_valid_jpeg(self, tmp_path):
        out = str(tmp_path / "scene.jpg")
        render_scene(out, count=2, timestamp="test", seed=1)
        assert os.path.isfile(out)
        # JPEG magic bytes
        with open(out, "rb") as f:
            assert f.read(2) == b"\xff\xd8"

    def test_anomaly_renders(self, tmp_path):
        out = str(tmp_path / "anom.jpg")
        render_scene(out, count=1, anomaly=True, timestamp="test", seed=2)
        assert os.path.getsize(out) > 0
