#!/bin/sh
# Token InfluxDB write-only con scope al bucket 'sentinel' para Node-RED. Desde deploy/.
set -e
ORG="${ORG:-sentinel}"; BUCKET="${BUCKET:-sentinel}"
BID=$(docker compose exec -T influxdb influx bucket list --org "$ORG" --name "$BUCKET" --hide-headers 2>/dev/null | awk '{print $1}')
[ -z "$BID" ] && { echo "No encuentro el bucket '$BUCKET'"; exit 1; }
docker compose exec -T influxdb influx auth create --org "$ORG" --write-bucket "$BID" \
  --description "nodered-writer (write-only, scoped)"
echo ">> Copia el token a Node-RED y retira el admin token."
