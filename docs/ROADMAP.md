# 🗺️ Roadmap

Where `sentinel-node` goes from a sim-first proof to a hardened field device.
Three tracks: **real sensors**, **transport security (TLS)**, and **defense
in depth**. Ordered roughly by dependency.

---

## 1. Real sensors — swap sim → hardware, one adapter at a time

The hexagon makes this mechanical: implement each `Hw*` class in
`node/adapters/hw/sensors.py`, then flip the import in `runner/run_sim.py`.
The domain and application layers never change. Wiring, buses and drivers are
in [`node/adapters/hw/WIRING.md`](node/adapters/hw/WIRING.md).

### Node A — ambient + presence (ESP32, low power)
- [ ] **`HwBME680`** — I2C @ 0x76. Temperature / humidity / pressure / gas
      resistance. IAQ via Bosch BSEC (calibrated) or a heuristic from raw gas.
- [ ] **`HwLD2410`** — UART @ 256000. Parse the target frame → presence bit +
      per-gate distance. Optional OUT pin for a raw presence GPIO.
- [ ] Deep-sleep duty cycle (RTC wake) to run on battery/solar.

### Node B — edge ML (ESP32-S3, PSRAM)
- [ ] **`HwAudioML`** — INMP441 over I2S → MFCC features → TinyML classifier
      (TFLite-Micro / Edge Impulse) → `Event`. **Raw audio never leaves.**
- [ ] **`HwVisionCam`** — OV2640 → person detector / frame diff → `Event` with
      count + snapshot path. **JPEG saved out-of-band, never in the frame.**

### Shared
- [ ] `binary_codec.py` implementing `CodecPort` — struct-packed frames for the
      LoRa path (the presence/air node is LoRa-friendly; the ML node is WiFi).
- [ ] Calibration pass: BME680 gas baseline, LD2410 gate sensitivity, mic gain.

---

## 2. Transport security — TLS everywhere

Right now the sim publishes plaintext MQTT to `localhost` — fine for a local
demo, unacceptable on a real network. Harden the wire:

- [ ] **MQTT over TLS (8883).** Switch Mosquitto to a TLS listener; give the
      `MqttTransport` adapter a CA cert + `tls_set()`. Self-signed CA for the
      lab, Let's Encrypt / internal CA for anything routable.
- [ ] **Client certificates (mTLS).** Each node presents a cert; the broker
      rejects unknown clients. This is the real access-control boundary for
      IoT — a leaked password is replaceable, a per-device cert is revocable.
- [ ] **InfluxDB & Grafana behind TLS.** Terminate at a reverse proxy (Caddy /
      Traefik) so tokens and dashboards never travel in the clear.
- [ ] **Rotate the dev token.** `sentinel-local-dev-token` is a placeholder;
      generate a scoped, least-privilege token per writer (Node-RED gets
      write-only to the `sentinel` bucket, nothing else).

Adapter sketch (no core change — TLS lives entirely in the transport adapter):

```python
# node/adapters/transport/mqtt_tls.py
client.tls_set(ca_certs="ca.crt", certfile="node.crt", keyfile="node.key")
client.tls_insecure_set(False)
client.connect(host, 8883)
```

---

## 3. Defense in depth — security beyond transport

The project's angle is *physical/space security*; the software should match.

- [ ] **Payload integrity.** Sign or HMAC each frame so a spoofed MQTT publish
      can't inject fake occupancy/anomaly events. The `CodecPort` is the
      natural place — add a keyed MAC over the encoded bytes.
- [ ] **Rate limiting / anomaly on the ingest.** A node suddenly emitting 100×
      its normal frame rate is itself a signal (compromised or faulty). Flag it
      in Node-RED.
- [ ] **Secrets management.** Move tokens/certs out of compose env vars into a
      secrets store (Docker secrets, or Vault if you want to tie it to your
      `aegisvault` work). No credentials in the repo, ever — `.env` is
      git-ignored and `.env.example` documents the shape.
- [ ] **Audit trail.** Persist a tamper-evident log of security-relevant events
      (anomaly detections, node disconnects, auth failures) — a hash-chain like
      the one in `aegis-zero-trust` fits here.
- [ ] **Privacy by design, documented.** Make the "raw media never leaves the
      device" guarantee explicit and testable: a CI check that no adapter ever
      puts `bytes` into an `Event`. Turn the design decision into an enforced
      invariant, like the hexagon fitness tests already do.
- [ ] **Network segmentation.** Nodes on an isolated IoT VLAN; only the broker
      is reachable from them; Grafana/InfluxDB on the trusted side.

---

## Stretch

- [ ] Home Assistant integration (MQTT discovery) for the presence/air data.
- [ ] Over-the-air firmware updates with signature verification.
- [ ] Multi-node fleet: several `device_id`s, a Grafana variable to switch
      between rooms, per-node health panel.
