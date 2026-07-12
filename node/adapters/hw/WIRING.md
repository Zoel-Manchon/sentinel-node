# Hardware plan — sentinel-node

Two physical nodes make sense (they have different power/compute needs), or one
ESP32-S3 if you want everything on a single board. Pick per sensor.

## Node A — ambient + presence (ESP32 DevKit, low power)

| Peripheral | Bus  | Pins (ESP32)             | Notes |
|-----------|------|--------------------------|-------|
| BME680    | I2C0 | SDA=21, SCL=22, addr 0x76 | gas heater; 5 s warm-up |
| LD2410    | UART2| RX=16, TX=17, 256000 8N1  | + optional OUT pin → GPIO for a raw presence bit |

Driver notes:
- **BME680**: `robert-hh/BME680` for raw gas resistance, or the Bosch **BSEC**
  blob if you want a calibrated IAQ index (heavier; needs the closed-source lib).
- **LD2410**: parse the target frame (`0xF4F3F2F1 … 0xF8F7F6F5`); it gives moving
  + static target distance and an energy value per gate. UART default 256000.

## Node B — edge ML (ESP32-S3, needs PSRAM + more compute)

| Peripheral | Bus  | Pins                     | Notes |
|-----------|------|--------------------------|-------|
| INMP441   | I2S  | SCK=18, WS=19, SD=23      | 24-bit MEMS mic; classify on-device |
| OV2640    | (cam)| ESP32-CAM pin map         | person detect on-device |

Driver / model notes:
- **Audio**: capture a window over I2S → MFCC features → a small TFLite-Micro /
  Edge Impulse model → emit `Event("audio", label, conf)`. **Raw audio never
  leaves the device** — only the verdict is published. That's the privacy story.
- **Vision**: OV2640 frame → frame-diff or a tiny person detector → emit
  `Event("vision", "person", conf, {count, snapshot})`. The JPEG is saved
  out-of-band (SD card / HTTP POST) and only its **path** goes in the event.
  Never put the image in the telemetry frame — InfluxDB is a TSDB, not a blob store.

## Why the Measurement/Event split matters

`node/domain/model.py` has two types on purpose:
- **Measurement** = scalar (temp, distance, IAQ) → InfluxDB `telemetry` measurement.
- **Event** = discrete classification (sound class, person count) → InfluxDB
  `events` measurement, with label/channel as tags.

The Node-RED flow (`flows-sentinel.json`) splits them into two InfluxDB
measurements automatically. This keeps the time-series clean and lets Grafana
chart "confidence over time" for events separately from continuous readings.

## Porting note

`node/domain` and `node/application` are MicroPython-safe (no
typing/dataclasses/abc/enum). Copy them verbatim to each board; only the
adapters and the composition root differ between desktop sim and firmware.
