#!/usr/bin/env bash
# Every pack of one block: <block-id> <workdir> -> <workdir>/<member>/ (the pack files) and <workdir>/<member>.entry.json
# per member. A standalone country is a block of one and is built as before. A block of several gets one Valhalla
# graph over the members' merged extracts, split per member outline, so the app routes across the members; the base
# map, search and cue tables stay per member, from the member's own extract. All members share the block's version
# (the oldest extract date): the app routes across members of one version only.
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: $0 <block-id> <workdir>" >&2; exit 2; }
BLOCK=$1
mkdir -p "$2"
W=$(cd "$2" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/.."

members=$(uv run python -c "
from mapspack.config import blocks, load_countries
for c in blocks(load_countries()[0])['$BLOCK']: print(c.id, c.geofabrik)")
[ -n "$members" ] || { echo "unknown block $BLOCK" >&2; exit 2; }

pbfs=()
while read -r id path; do
  echo "== $id: extract"
  curl -fsSL -o "$W/$id.osm.pbf" "https://download.geofabrik.de/${path}-latest.osm.pbf"
  ls -l "$W/$id.osm.pbf"
  pbfs+=("$W/$id.osm.pbf")
  echo "== $id: tables"
  uv run python -m mapspack tables "$id" "$W/$id.osm.pbf" "$W/$id"
  echo "== $id: base map"
  scripts/build_basemap.sh "$W/$id.osm.pbf" "$W/$id"
done <<< "$members"

ids=$(cut -d' ' -f1 <<< "$members")
if [ "$(wc -l <<< "$members")" -eq 1 ]; then
  echo "== $BLOCK: Valhalla"
  scripts/build_valhalla.sh "${pbfs[0]}" "$W/$ids"
  rm -f "$W/$ids/valhalla.json"
else
  echo "== $BLOCK: merged extract"
  # osmium merge streams the sorted extracts and keeps one copy of what both hold along the border
  docker run --rm -v "$W:/w" debian:trixie sh -c "apt-get update -q > /dev/null && apt-get install -yq osmium-tool > /dev/null \
    && osmium merge --overwrite -o /w/block.osm.pbf $(for p in "${pbfs[@]}"; do printf '/w/%s ' "$(basename "$p")"; done)"
  ls -l "$W/block.osm.pbf"
  echo "== $BLOCK: Valhalla"
  scripts/build_valhalla.sh "$W/block.osm.pbf" "$W/block"
  echo "== $BLOCK: split"
  uv run python -m mapspack split "$W/block/valhalla_tiles.tar" $(for id in $ids; do printf '%s=%s ' "$id" "$W/$id"; done)
  rm -rf "$W/block" "$W/block.osm.pbf"
fi

version=$(uv run python -m mapspack version "${pbfs[@]}")
for id in $ids; do
  uv run python -m mapspack entry --version "$version" "$id" "$W/$id.osm.pbf" "$W/$id" > "$W/$id.entry.json"
  python3 -c "import json; e=json.load(open('$W/$id.entry.json')); print(e['id'], e['version'], e.get('block'), [(f['name'], f['size']) for f in e['files']])"
  rm -f "$W/$id.osm.pbf"
done
