# 🛠️ Setup guide

Step-by-step deployment of the full `sentinel-node` stack, from zero to a live
Grafana dashboard. Windows + Docker Desktop + Node-RED (npm) assumed; the
commands are the same on Linux/macOS bar the venv activation path.

Each step ends with a **✅ Verify** — if it passes, move on; if not, the
problem is right there, not three steps later.

---

## Prerequisites

- Python 3.10+
- Docker Desktop (running)
- Node.js + Node-RED (`npm install -g node-red`)

---

## Step 0 — Project & tests

```bash
cd sentinel-node
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,mqtt]"
pytest
```

**✅ Verify:** `38 passed`. The hexagon and adapters are healthy; everything
from here is infrastructure.

---

## Step 1 — Docker containers

With Docker Desktop **running** (whale icon stable):

```bash
docker compose -f deploy/docker-compose.yml up -d
```

Starts three containers: Mosquitto (MQTT broker), InfluxDB 2, Grafana.

```bash
docker ps
```

**✅ Verify:** three containers `Up` — `eclipse-mosquitto`, `influxdb`,
`grafana`. If one is missing or `Exited`, check its log:
`docker logs sentinel-stack-<name>-1`.

> InfluxDB self-provisions **only on first boot with an empty volume**: org
> `sentinel`, bucket `sentinel`, token `sentinel-local-dev-token`. If you ran
> this stack before with a different volume, those vars are ignored — run
> `docker compose -f deploy/docker-compose.yml down -v` and bring it up again.

---

## Step 2 — InfluxDB check

Open `http://localhost:8086`, log in with `sentinel` / `sentinel-local-dev-only`.

**✅ Verify:** you reach the dashboard and see the `sentinel` bucket under
Load Data → Buckets (empty for now — expected).

---

## Step 3 — Node-RED: MQTT → InfluxDB bridge

In a **separate** terminal (leave it running):

```bash
node-red
```

Open `http://localhost:1880`, then:

**3a. Install the InfluxDB palette.** Menu (☰) → Manage palette → Install →
search `node-red-contrib-influxdb` → Install.

**3b. Import the flow.** Menu → Import → paste the contents of
`deploy/nodered/flows-sentinel.json` → Import.

**3c. Set the InfluxDB token.** Two green output nodes appear (`readings`,
`events`). Double-click `readings` → pencil next to the influxdb2 server →
in the server form:
- Version: `2.0`
- URL: `http://localhost:8086`
- **Token**: `sentinel-local-dev-token`
- Organization: `sentinel`

Update → Done. Both nodes share the server, so once is enough.

**3d. Deploy** (red button, top right).

**✅ Verify:** the `iot/+/state` input node shows a green **connected** badge.
If it says connecting/disconnected, the broker isn't reachable — check
Mosquitto is in `docker ps` and the broker node points to `localhost:1883`.

---

## Step 4 — Feed data with the simulator

Back in the project terminal (venv active):

```bash
python -m runner.run_sim --mqtt localhost --speed 120 --interval 60 \
    --anomaly-at 4 --anomaly-label glass_break
```

Lines like `[frame 0000] sentinel-01 ...` scroll by — each is a frame over MQTT.

**✅ Verify the whole chain:** no red errors under the InfluxDB nodes in
Node-RED, and in `http://localhost:8086` → Data Explorer → bucket `sentinel`
you see two measurements: `telemetry` (scalar readings) and `events`
(classifications). Points arriving there means the **whole pipeline works**.

> `unauthorized` error in Node-RED → the token in step 3c is wrong/empty.

---

## Step 5 — Grafana: datasource

Open `http://localhost:3000`, log in `admin` / `admin` (Skip the password
change if you like).

Menu ☰ → Connections → Data sources → Add data source → **InfluxDB**:
- **Query language:** `Flux` (top dropdown — not InfluxQL)
- **URL:** `http://influxdb:8086` (container name — Grafana is inside the Docker network)
- InfluxDB Details → Organization `sentinel`, Token `sentinel-local-dev-token`,
  Default Bucket `sentinel`

**Save & test.**

**✅ Verify:** green "datasource is working / 1 buckets found". If it fails with
connection refused, use `http://host.docker.internal:8086`.

---

## Step 6 — Grafana: dashboard

Menu ☰ → Dashboards → New → Import → Upload JSON file →
`deploy/grafana/dashboard-sentinel.json` → map `DS_INFLUXDB` to the datasource
→ Import.

**✅ Verify:** with the simulator running and range "Last 30 minutes" @ 5s
refresh, panels fill within seconds — gauges for temp/IAQ/humidity, the
OCCUPIED/CLEAR presence stat, and around minute 4 the audio panel spikes near
confidence 1.0 on the `glass_break`.

---

## Step 7 — Camera snapshots & gallery (optional)

The vision sim writes a real snapshot per detection. Two ways to view them.

**7a. Generate a realistic image bank (optional, needs an API key).**
Without this, the sim renders Pillow placeholder frames (silhouettes) — the
pipeline works with zero setup. For realistic CCTV-style frames:

```bash
pip install -e ".[ai]"
export OPENAI_API_KEY=sk-...          # Windows: set OPENAI_API_KEY=sk-...
python tools/generate_bank.py --backend openai --out docs/bank
```

This creates 5 reference frames once (empty / one / two / three / anomaly).
Then run the sim pointing at the bank:

```bash
python -m runner.run_sim --mqtt localhost --speed 120 --anomaly-at 4 \
    --bank docs/bank --snapshot-dir C:/sentinel/snaps
```

**7b. Serve the gallery from Node-RED.** The flow already includes
`GET /gallery` and `GET /snap/:file`. Point them at the snapshot dir: in
Node-RED, set an environment variable `SNAPSHOT_DIR` to the **absolute** path
you passed to `--snapshot-dir` (Menu → Settings, or set it in the OS before
`node-red`). Then open:

```
http://localhost:1880/gallery
```

**✅ Verify:** a dark auto-refreshing gallery of the latest camera snapshots,
each labelled with person count and time.

> Use an absolute `--snapshot-dir` shared between the runner and Node-RED (e.g.
> `C:/sentinel/snaps`), so both processes read/write the same folder.

---

## Daily startup (after first setup)

Grafana and InfluxDB keep their config in Docker volumes, so it's just:

```bash
docker compose -f deploy/docker-compose.yml up -d   # 1. containers
node-red                                            # 2. Node-RED (flow saved)
python -m runner.run_sim --mqtt localhost --speed 120 --anomaly-at 4   # 3. sim
```

---

## Troubleshooting — 30-second triage

Find **where the chain breaks**:

| Check | If NO |
|-------|-------|
| `docker ps` shows 3 containers `Up`? | Docker problem — check `docker logs` |
| Node-RED MQTT node green "connected"? | Broker unreachable — check Mosquitto + `localhost:1883` |
| `telemetry` + `events` appear in InfluxDB Data Explorer? | Sim stopped, or Node-RED not writing (token) |
| Grafana → Explore with a simple Flux query returns data? | If yes but dashboard is blank → panel config or time window (use "Last 6 hours" while debugging) |

Most common causes: the simulator stopped (the 30-min window empties), or the
InfluxDB token is wrong in Node-RED.

---

## Reset everything

```bash
# Docker: containers + volumes + images
docker compose -f deploy/docker-compose.yml down -v

# Node-RED: wipe flows/credentials/palette (host install)
# Windows PowerShell:
Remove-Item -Recurse -Force $env:USERPROFILE\.node-red
```

Then repeat from Step 1 — a clean slate self-provisions again.
