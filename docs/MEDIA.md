# 📸 Media guide — screenshots & demo

What to capture for the README, and how. Files go in `docs/` and are already
referenced by the README (`demo.gif`) or the screenshots section you can add.

## The demo GIF (`docs/demo.gif`)

The money shot. A simulated day compressed into minutes, with the acoustic
anomaly as the climax.

1. Start the full stack (see `SETUP.md`) and confirm data flows.
2. Run the sim with the anomaly cued a few minutes in:
   ```bash
   python -m runner.run_sim --mqtt localhost --speed 120 --interval 60 \
       --anomaly-at 4 --anomaly-label glass_break
   ```
3. Grafana dashboard → range **Last 30 minutes**, refresh **5s**, browser
   **fullscreen (F11)** so no toolbar shows.
4. Wait ~2 min for curves to build, then record **20–30 seconds** that capture:
   - the gauges moving (temp / IAQ / humidity),
   - the presence stat flipping **CLEAR → OCCUPIED** (background changes),
   - around minute 4, the **audio panel spiking to ~1.0** on the glass_break.
5. Tool: **ScreenToGif** (Windows, free). Export ~800px wide, 10–15 fps,
   **under 10 MB** (GitHub renders inline up to that). Trim duration before
   dropping resolution.

## Screenshots (`docs/*.png`)

Capture these four, then drop the gallery block below into the README (right
before "Hardware phase"):

| File | What to capture |
|------|-----------------|
| `dashboard.png` | Full dashboard, a busy midday moment — gauges lit, presence OCCUPIED, audio points visible |
| `dashboard_events.png` | Close-up of the audio-events panel with a glass_break point near confidence 1.0 |
| `node_red.png` | The Node-RED flow showing the `frame → readings + events` split node with two outputs wired to two InfluxDB nodes |
| `influxdb.png` | InfluxDB Data Explorer showing **both** `telemetry` and `events` measurements — proves the readings/events split works |

Gallery markdown to paste into the README:

```markdown
## Screenshots

| Grafana — live dashboard | Audio events — confidence |
|:---:|:---:|
| ![dashboard](docs/dashboard.png) | ![events](docs/dashboard_events.png) |

| Node-RED — readings/events split | InfluxDB — two measurements |
|:---:|:---:|
| ![node-red](docs/node_red.png) | ![influxdb](docs/influxdb.png) |
```

## Tips

- Record at a moment when the room is **occupied** (midday in sim time) so the
  presence/vision/audio panels all show activity at once — that coherence is
  the selling point.
- For a static hero image at full resolution, also save a `dashboard.png` with
  a full day visible ("Last 6 hours" range) — recruiters zoom into that.
- Keep the GIF focused: one clear story (empty → occupied → anomaly), not a
  random 60-second scroll.
