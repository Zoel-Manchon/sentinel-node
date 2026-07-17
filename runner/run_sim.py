"""Composition root — the ONLY place concrete adapters meet use cases.

    python -m runner.run_sim                              # console, real time
    python -m runner.run_sim --speed 120                  # a day in 12 min
    python -m runner.run_sim --mqtt localhost --speed 120
    python -m runner.run_sim --anomaly-at 3               # scripted glass-break

Enable/disable each sensor with --no-air / --no-presence / --no-audio / --no-vision.
When the hardware arrives, swap Sim* for Hw* imports here (and only here),
sensor by sensor — the ones you don't have yet stay simulated.
"""

import argparse
import os
import sys

from node.adapters.codec.json_codec import JsonCodec
from node.adapters.security.hmac_signer import HmacSigner
from node.adapters.security.keyring import derive_key
from node.adapters.security.signed_codec import SignedCodec
from node.adapters.sim.clock import SimClock, SystemClock
from node.adapters.sim.environment import SpaceWorld
from node.adapters.sim.sensors import (
    SimAudioML,
    SimBME680,
    SimLD2410,
    SimPowerMonitor,
    SimVisionCam,
)
from node.adapters.transport.console import ConsoleTransport
from node.application.collect import CollectTelemetry, PublishTelemetry
from node.application.scheduler import DutyCycleScheduler


class _AnomalyCue:
    """Fires a scripted acoustic anomaly once the virtual clock passes the cue.
    Demo-only, lives in the composition root."""

    def __init__(self, publish, world, clock, at_epoch, label, duration_s):
        self._publish = publish
        self._world = world
        self._clock = clock
        self._at = at_epoch
        self._label = label
        self._duration_s = duration_s
        self._fired = False

    def execute(self):
        if not self._fired and self._clock.now() >= self._at:
            self._world.force_anomaly(self._label, self._duration_s)
            self._fired = True
        return self._publish.execute()


def build_scheduler(args):
    clock = SimClock(speed=args.speed) if args.speed != 1.0 else SystemClock()
    world = SpaceWorld(clock, seed=args.seed)

    sensors = []
    detectors = []
    if not args.no_air:
        sensors.append(SimBME680(world, fail_rate=args.fail_rate))
    if not args.no_presence:
        sensors.append(SimLD2410(world, fail_rate=args.fail_rate))
    if not args.no_audio:
        detectors.append(SimAudioML(world))
    if not args.no_vision:
        detectors.append(SimVisionCam(
            world, snapshot_dir=args.snapshot_dir, bank_dir=args.bank,
            write_images=not args.no_snapshots))

    power = SimPowerMonitor(world)

    if args.mqtt:
        from node.adapters.transport.mqtt_direct import MqttTransport
        transport = MqttTransport(host=args.mqtt, port=args.mqtt_port)
    else:
        transport = ConsoleTransport()

    collector = CollectTelemetry(args.device_id, sensors, clock,
                                 detectors=detectors, power=power)
    codec = JsonCodec()
    if args.sign:
        master = os.environ.get("SENTINEL_MASTER_SECRET", "change-me").encode("utf-8")
        signer = HmacSigner(derive_key(master, args.device_id), key_id=args.device_id)
        codec = SignedCodec(codec, signer=signer)  # payload integrity (HMAC)
    publisher = PublishTelemetry(collector, codec, transport)

    if args.anomaly_at is not None:
        publisher = _AnomalyCue(
            publisher, world, clock,
            at_epoch=clock.now() + int(args.anomaly_at * 60),
            label=args.anomaly_label,
            duration_s=int(args.anomaly_duration),
        )

    return DutyCycleScheduler(publisher, clock, interval_seconds=args.interval), transport


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="run_sim", description="Simulated sentinel node")
    p.add_argument("--device-id", default="sentinel-01")
    p.add_argument("--sign", action="store_true",
                   help="HMAC-sign each frame (payload integrity; key_id = device-id)")
    p.add_argument("--interval", type=int, default=60,
                   help="seconds between frames (virtual if --speed > 1)")
    p.add_argument("--speed", type=float, default=1.0,
                   help="time acceleration (120 = a day in 12 min)")
    p.add_argument("--cycles", type=int, default=0, help="0 = forever")
    p.add_argument("--mqtt", metavar="HOST", default=None)
    p.add_argument("--mqtt-port", type=int, default=1883)
    p.add_argument("--fail-rate", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--no-air", action="store_true", help="disable BME680 sim")
    p.add_argument("--no-presence", action="store_true", help="disable LD2410 sim")
    p.add_argument("--no-audio", action="store_true", help="disable audio ML sim")
    p.add_argument("--no-vision", action="store_true", help="disable vision cam sim")
    p.add_argument("--bank", default=None, metavar="DIR",
                   help="AI snapshot bank dir (see tools/generate_bank.py); "
                        "falls back to Pillow placeholders if absent")
    p.add_argument("--snapshot-dir", default="docs/snapshots/cam-01",
                   help="where vision snapshots are written")
    p.add_argument("--no-snapshots", action="store_true",
                   help="don't write image files (events still carry the path)")
    p.add_argument("--anomaly-at", type=float, default=None, metavar="MIN",
                   help="force an acoustic anomaly after MIN virtual minutes")
    p.add_argument("--anomaly-label", default="glass_break")
    p.add_argument("--anomaly-duration", type=float, default=20.0, metavar="SEC")
    args = p.parse_args(argv)

    scheduler, transport = build_scheduler(args)

    def on_frame(frame):
        ev = ", ".join("%s=%s" % (e.channel, e.label) for e in frame.events)
        sys.stderr.write("[frame %04d] %s @ %d  m=%d  [%s]\n"
                         % (frame.sequence, frame.device_id, frame.timestamp,
                            len(frame.measurements), ev))

    def on_error(exc):
        sys.stderr.write("[error] %r\n" % exc)

    try:
        scheduler.run(cycles=args.cycles, on_frame=on_frame, on_error=on_error)
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
