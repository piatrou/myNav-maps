#!/usr/bin/env bash
# Valhalla routing tiles for one country: <pbf> -> <outdir>/valhalla_tiles.tar
# The Valhalla version must match the one inside the app (valhalla-mobile 0.6.4 = Valhalla 3.9.1): tiles from
# another version do not load. Admins (driving side, country), time zones and elevation (grades for the cues) are in.
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: $0 <pbf> <outdir>" >&2; exit 2; }
PBF=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
OUT=$(mkdir -p "$2" && cd "$2" && pwd)
IMAGE=ghcr.io/valhalla/valhalla:3.9.1

docker run --rm -v "$PBF:/in/extract.osm.pbf:ro" -v "$OUT:/out" --entrypoint bash "$IMAGE" -c '
set -euo pipefail
W=/work; mkdir -p $W/tiles $W/elevation
step() { local t0=$SECONDS; "$@" > $W/step.log 2>&1 || { tail -40 $W/step.log; exit 1; }; echo "$1 ${*:2:2}: $((SECONDS - t0)) s"; }
valhalla_build_config --mjolnir-tile-dir $W/tiles --mjolnir-tile-extract /out/valhalla_tiles.tar \
  --mjolnir-admin $W/admins.sqlite --mjolnir-timezone $W/timezones.sqlite \
  --additional-data-elevation $W/elevation --mjolnir-concurrency $(nproc) > $W/valhalla.json
step valhalla_build_admins -c $W/valhalla.json /in/extract.osm.pbf
step valhalla_build_timezones $W/valhalla.json
step valhalla_build_tiles -c $W/valhalla.json -e bss /in/extract.osm.pbf
step valhalla_build_elevation --from-tiles --decompress -c $W/valhalla.json
step valhalla_build_tiles -c $W/valhalla.json -s hierarchy /in/extract.osm.pbf
step valhalla_build_extract -c $W/valhalla.json -v
cp $W/valhalla.json /out/valhalla.json
'
ls -l "$OUT/valhalla_tiles.tar"
