"""Image bank — maps an occupancy scene to a cached snapshot file.

The vision sim doesn't generate an image per frame (that'd be slow and, with an
AI backend, expensive). Instead a small bank is generated ONCE (empty / 1p /
2p / 3p+ / anomaly) and cached on disk; each detection just resolves the
current scene to the right cached file and copies it to a per-event snapshot
path. This mirrors how a real node with pre-captured reference frames would
behave.

Bank layout (under bank_dir):
    empty.jpg  one.jpg  two.jpg  three.jpg  anomaly.jpg

If the bank is missing, callers fall back to the Pillow placeholder generator
(see placeholder.py) so the project works with zero setup.
"""

import os

SCENES = ("empty", "one", "two", "three", "anomaly")


def scene_for(count: int, anomaly: bool = False) -> str:
    if anomaly:
        return "anomaly"
    if count <= 0:
        return "empty"
    if count == 1:
        return "one"
    if count == 2:
        return "two"
    return "three"


class ImageBank:
    """Resolves a scene name to a cached file in bank_dir. Read-only."""

    def __init__(self, bank_dir: str):
        self._dir = bank_dir

    def path_for(self, scene: str) -> str:
        return os.path.join(self._dir, "%s.jpg" % scene)

    def has(self, scene: str) -> bool:
        return os.path.isfile(self.path_for(scene))

    def is_complete(self) -> bool:
        return all(self.has(s) for s in SCENES)

    def resolve(self, count: int, anomaly: bool = False) -> str:
        """Return the cached file path for this scene, or None if absent."""
        scene = scene_for(count, anomaly)
        p = self.path_for(scene)
        return p if os.path.isfile(p) else None
