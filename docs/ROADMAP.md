# 🗺️ Roadmap

Where `sentinel-node` goes from a sim-first proof to a hardened field device.
Three tracks: **real sensors**, **transport security (TLS)**, and **defense
in depth** — then integration onto a hardened OS. Ordered roughly by dependency.

**Status:** Track 2 ✅ done · Track 3 ✅ mostly done · Track 1 ⏳ waiting on hardware.

---

## 1. Real sensors — swap sim → hardware, one adapter at a time &nbsp; ⏳ *waiting on hardware*

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
      LoRa path *(doable now — pure logic, no hardware needed)*.
- [ ] Calibration pass: BME680 gas baseline, LD2410 gate sensitivity, mic gain.

---

## 2. Transport security — TLS everywhere &nbsp; ✅ **done**

The sim used to publish plaintext MQTT to `localhost`. The wire is now hardened:

- [x] **MQTT over TLS (8883).** Mosquitto runs a TLS listener; the
      `MqttTlsTransport` adapter connects with a CA cert + `tls_set()`.
- [x] **Client certificates (mTLS).** Each node presents its own cert
      (`CN = node-id = key_id`); the broker rejects unknown clients and can
      revoke a single node via CRL — the real access boundary for field IoT.
- [x] **InfluxDB & Grafana behind TLS.** Terminated at a Caddy reverse proxy
      (`:3443` / `:8443`), so tokens and dashboards never travel in the clear.
- [x] **Scoped token.** The dev admin token is retired in favour of a
      write-only, bucket-scoped token for the Node-RED writer.

TLS lives entirely in the transport adapter — the core never changed:

```python
# node/adapters/transport/mqtt_tls.py
client.tls_set(ca_certs="ca.crt", certfile="node.crt", keyfile="node.key")
client.tls_insecure_set(False)
client.connect(host, 8883)
```

---

## 3. Defense in depth — security beyond transport &nbsp; ✅ *mostly done*

The project's angle is *physical/space security*; the software matches it.

- [x] **Payload integrity.** Each frame is HMAC-signed (`--sign`) with the
      node's per-node key, so a spoofed MQTT publish can't inject fake
      occupancy/anomaly events. The MAC rides over the encoded bytes at the
      `CodecPort` (`SignedCodec`); the gateway verifies and rejects on mismatch.
- [x] **Secrets management.** Tokens/certs stay out of the repo: `.env` is
      git-ignored and `.env.example` documents the shape; keys are per-node.
- [x] **Audit trail.** A tamper-evident hash-chain log of security events
      (anomaly detections, node disconnects, auth failures), like the ledger in
      `aegis-zero-trust`.
- [x] **Privacy by design, enforced.** The "raw media never leaves the device"
      guarantee is now a CI-checked invariant: an `Event` refuses any `bytes`
      payload. The design decision is enforced, like the hexagon fitness tests.
- [ ] **Rate limiting / anomaly on the ingest.** A node suddenly emitting 100×
      its normal frame rate is itself a signal — flag it in Node-RED.
- [ ] **Network segmentation.** Nodes on an isolated IoT VLAN; only the broker
      is reachable from them; Grafana/InfluxDB on the trusted side.

---

## 4. Next — run it on a hardened OS (Emberwall)

The natural next step: stop trusting the gateway host implicitly and **run the
MQTT broker/gateway on an [Emberwall](https://github.com/Zoel-Manchon/emberwall)
appliance** — a minimal, immutable, hardened Linux (default-deny nftables, no
interactive login, hardened kernel). This closes the last residual risk (a
compromised gateway host) and pushes defense in depth all the way down to the OS:

- [ ] Package the broker + gateway as an Emberwall `appliance` image.
- [ ] Move network segmentation (§3) onto the Emberwall firewall — only the
      broker port is reachable from the IoT VLAN.
- [ ] Ship `sentinel` (Emberwall's built-in tool) alongside for on-box scanning.

Application-layer security → transport security → **OS-level hardening**: the
whole stack defended, sensor to kernel.

---

## Stretch

- [ ] Home Assistant integration (MQTT discovery) for the presence/air data.
- [ ] Over-the-air firmware updates with signature verification.
- [x] Multi-node fleet: several `device_id`s, a per-node Grafana variable +
      health panel *(pattern proven in `agrisentinel`)*.
