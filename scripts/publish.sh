#!/usr/bin/env bash
# Cloudflare R2 through its S3 API. Needs R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in the environment.
#   publish.sh pack <packdir> <prefix>     upload the pack files under <prefix> (packs/<id>/<version>/)
#   publish.sh get-manifest <out>          current manifest.json into <out>; no file when there is none yet
#   publish.sh put-manifest <file>         switch the manifest: always the last step of a publish
#   publish.sh list                        {"<id>": [versions]} of what the bucket holds, as JSON
#   publish.sh delete <prefix>             remove a retired version
set -euo pipefail
BUCKET=mynav-maps
: "${R2_ACCOUNT_ID:?}" "${R2_ACCESS_KEY_ID:?}" "${R2_SECRET_ACCESS_KEY:?}"
export AWS_ACCESS_KEY_ID=$R2_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY=$R2_SECRET_ACCESS_KEY AWS_DEFAULT_REGION=auto
s3() { aws s3 --endpoint-url "https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com" --only-show-errors "$@"; }
FILES="valhalla_tiles.tar lanes.json landmarks.json basemap.mbtiles search.sqlite zones.json"

case "${1:-}" in
  pack)
    for f in $FILES; do
      [ -f "$2/$f" ] && s3 cp "$2/$f" "s3://$BUCKET/$3$f"
    done ;;
  get-manifest)
    s3 cp "s3://$BUCKET/manifest.json" "$2" 2>/dev/null || rm -f "$2" ;;
  put-manifest)
    s3 cp "$2" "s3://$BUCKET/manifest.json" --content-type application/json --cache-control no-cache ;;
  list)
    python3 - "$(s3 ls "s3://$BUCKET/packs/" --recursive || true)" <<'PY'
import json, sys
out = {}
for line in sys.argv[1].splitlines():
    parts = line.split()[-1].split("/")  # packs/<id>/<version>/<file>
    if len(parts) >= 4:
        out.setdefault(parts[1], set()).add(parts[2])
print(json.dumps({k: sorted(v) for k, v in out.items()}))
PY
    ;;
  delete)
    [[ "$2" == packs/*/*/ ]] || { echo "refusing to delete $2" >&2; exit 2; }
    s3 rm "s3://$BUCKET/$2" --recursive ;;
  *) sed -n 2,8p "$0" >&2; exit 2 ;;
esac
