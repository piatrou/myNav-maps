#!/usr/bin/env bash
# Offline base map for one country: <pbf> -> <outdir>/basemap.mbtiles, OpenMapTiles schema (the app's five styles).
# planetiler downloads its other sources (water polygons, Natural Earth, lakes) into a cache it deletes after.
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: $0 <pbf> <outdir>" >&2; exit 2; }
PBF=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
OUT=$(mkdir -p "$2" && cd "$2" && pwd)
CACHE=$(mktemp -d)
trap 'rm -rf "$CACHE"' EXIT
t0=$SECONDS
docker run --rm -v "$PBF:/in/extract.osm.pbf:ro" -v "$OUT:/out" -v "$CACHE:/cache" \
  ghcr.io/onthegomap/planetiler:0.10.2 \
  --osm-path=/in/extract.osm.pbf --download --download-dir=/cache --tmpdir=/cache/tmp \
  --output=/out/basemap.mbtiles --force > "$CACHE/planetiler.log" 2>&1 || { tail -40 "$CACHE/planetiler.log"; exit 1; }
echo "planetiler: $((SECONDS - t0)) s"
ls -l "$OUT/basemap.mbtiles"
