#!/usr/bin/env bash
# Offline base map for one country: <pbf> -> <outdir>/basemap.mbtiles, OpenMapTiles schema (the app's five styles).
# The sea is built from the extract's own coastline with osmcoastline (the tool osmdata.openstreetmap.de uses), so
# the build does not depend on that server; a landlocked country gets an empty water layer. planetiler downloads its
# remaining sources (Natural Earth, lake centerlines) into a scratch dir removed afterwards.
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: $0 <pbf> <outdir>" >&2; exit 2; }
PBF=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
OUT=$(mkdir -p "$2" && cd "$2" && pwd)
CACHE=$(mktemp -d)
cleanup() { docker run --rm -v "$CACHE:/c" debian:trixie sh -c 'rm -rf /c/*' >/dev/null 2>&1 || true; rm -rf "$CACHE"; }
trap cleanup EXIT

t0=$SECONDS
docker run --rm -v "$PBF:/in/extract.osm.pbf:ro" -v "$CACHE:/c" debian:trixie bash -c '
set -euo pipefail
apt-get update -qq > /dev/null && apt-get install -yqq osmcoastline gdal-bin zip > /dev/null 2>&1
cd /c
rc=0; osmcoastline -o coast.db --output-polygons=water --srs=3857 --max-points=1000 --overwrite \
  /in/extract.osm.pbf > coast.log 2>&1 || rc=$?
# 0 ok, 1 warnings, 2 coastline errors it worked around; 3 fatal (also: no coastline at all, a landlocked country)
if [ $rc -le 2 ] && ogr2ogr -f "ESRI Shapefile" water_polygons.shp coast.db water_polygons 2>> coast.log; then
  echo "coastline: $(ogrinfo -so water_polygons.shp water_polygons | sed -n "s/Feature Count: //p") water polygons (osmcoastline exit $rc)"
else
  echo "coastline: none (osmcoastline exit $rc), empty water layer"
  echo "{\"type\": \"FeatureCollection\", \"features\": []}" > empty.geojson
  ogr2ogr -f "ESRI Shapefile" -nlt POLYGON -a_srs EPSG:3857 -nln water_polygons water_polygons.shp empty.geojson
fi
zip -q water-polygons-split-3857.zip water_polygons.*
rm -f coast.db water_polygons.*
'
echo "coastline: $((SECONDS - t0)) s"

t0=$SECONDS
docker run --rm -v "$PBF:/in/extract.osm.pbf:ro" -v "$OUT:/out" -v "$CACHE:/cache" \
  ghcr.io/onthegomap/planetiler:0.10.2 \
  --osm-path=/in/extract.osm.pbf --download --download-dir=/cache --tmpdir=/cache/tmp \
  --water-polygons-path=/cache/water-polygons-split-3857.zip \
  --output=/out/basemap.mbtiles --force > "$CACHE/planetiler.log" 2>&1 || { tail -40 "$CACHE/planetiler.log"; exit 1; }
echo "planetiler: $((SECONDS - t0)) s"
ls -l "$OUT/basemap.mbtiles"
