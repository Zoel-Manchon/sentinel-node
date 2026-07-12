#!/usr/bin/env python3
"""Generate the AI snapshot bank — run ONCE, with your own API key.

Creates 5 realistic reference frames (empty / 1p / 2p / 3p+ / anomaly) that the
simulated camera then serves per scene. Generating a small bank once, instead
of one image per frame, keeps it fast and cheap.

Backends:
  --backend openai   uses OpenAI Images (gpt-image-1). Needs OPENAI_API_KEY.
  --backend none     just renders Pillow placeholders (no API, no key).

Usage:
  export OPENAI_API_KEY=sk-...
  python tools/generate_bank.py --backend openai --out docs/bank
  python tools/generate_bank.py --backend none  --out docs/bank   # offline

The sim picks up the bank automatically when you pass --bank docs/bank to
runner/run_sim.py (or it falls back to live Pillow placeholders).
"""

import argparse
import base64
import os
import sys


def _load_dotenv():
    """Load KEY=VALUE lines from a .env file in the project root, if present.

    Tiny parser (no dependency): only sets vars that aren't already in the
    environment, so a real env var still wins over the file.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

SCENES = {
    "empty": "An empty modern office room, security camera view, wide angle, "
             "no people, daytime, realistic CCTV still, muted colors.",
    "one": "A modern office room seen from a ceiling security camera, one person "
           "standing, realistic CCTV still, wide angle, daytime.",
    "two": "A modern office room seen from a ceiling security camera, two people "
           "standing and talking, realistic CCTV still, wide angle, daytime.",
    "three": "A modern office room seen from a ceiling security camera, three or "
             "more people, busy, realistic CCTV still, wide angle, daytime.",
    "anomaly": "A modern office room security camera view at night, a shattered "
               "glass window, alarm situation, dramatic red tint, realistic CCTV still.",
}


def gen_openai(prompt: str, out_path: str, size: str = "1024x1024"):
    from openai import OpenAI  # pip install openai
    client = OpenAI()
    resp = client.images.generate(model="gpt-image-1", prompt=prompt, size=size)
    b64 = resp.data[0].b64_json
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))


def gen_placeholder(scene: str, out_path: str):
    # reuse the project's Pillow generator
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from node.adapters.vision.bank import scene_for  # noqa: F401 (kept for parity)
    from node.adapters.vision.placeholder import render_scene
    count = {"empty": 0, "one": 1, "two": 2, "three": 3, "anomaly": 1}[scene]
    render_scene(out_path, count, anomaly=(scene == "anomaly"),
                 timestamp="reference", seed=hash(scene) & 0xFFFF)


def main(argv=None):
    _load_dotenv()
    p = argparse.ArgumentParser(description="Generate the snapshot bank")
    p.add_argument("--backend", choices=["openai", "none"], default="none")
    p.add_argument("--out", default="docs/bank")
    p.add_argument("--size", default="1024x1024")
    args = p.parse_args(argv)

    key = os.environ.get("OPENAI_API_KEY", "")
    if args.backend == "openai" and (not key or key.startswith("sk-your-new-key")):
        print("! OPENAI_API_KEY missing or still the placeholder.")
        print("  Edit .env with a NEW key (revoke any key you've shared), then re-run.")
        print("  Generating Pillow placeholders instead so you have a working bank.\n")
        args.backend = "none"

    os.makedirs(args.out, exist_ok=True)
    for scene, prompt in SCENES.items():
        out_path = os.path.join(args.out, "%s.jpg" % scene)
        print("→ %-8s %s" % (scene, out_path))
        if args.backend == "openai":
            if not os.environ.get("OPENAI_API_KEY"):
                print("  ! OPENAI_API_KEY not set — falling back to placeholder")
                gen_placeholder(scene, out_path)
            else:
                gen_openai(prompt, out_path, size=args.size)
        else:
            gen_placeholder(scene, out_path)
    print("\nBank ready in %s — run the sim with:  --bank %s" % (args.out, args.out))


if __name__ == "__main__":
    main()
