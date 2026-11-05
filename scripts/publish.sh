#!/usr/bin/env bash
# Cloudflare R2 through its S3 API. Needs R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in the environment.
#   publish.sh pack <packdir> <prefix>     upload the pack files under <prefix> (packs/<id>/<version>/); refuses a
#                                          prefix that already holds files: a published version is never rewritten
#   publish.sh get-manifest <out>          current manifest.json into <out>; no file when there is none yet; any
#                                          other error fails (never mistake an outage for an empty bucket)
#   publish.sh put-manifest <file>         switch the manifest: always the last step of a publish
#   publish.sh list                        {"<id>": [versions]} of what the bucket holds, as JSON
#   publish.sh delete <prefix>             remove a retired version
set -euo pipefail
BUCKET=mynav-maps
: "${R2_ACCOUNT_ID:?}" "${R2_ACCESS_KEY_ID:?}" "${R2_SECRET_ACCESS_KEY:?}"
export AWS_ACCESS_KEY_ID=$R2_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY=$R2_SECRET_ACCESS_KEY AWS_DEFAULT_REGION=auto
# R2 does not take the newer default request checksums of AWS CLI v2.23+
export AWS_REQUEST_CHECKSUM_CALCULATION=when_required AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
s3() { aws s3 --endpoint-url "$ENDPOINT" "$@"; }
FILES="valhalla_tiles.tar lanes.json landmarks.json basemap.mbtiles search.sqlite zones.json"

case "${1:-}" in
  pack)
    if [ -n "$(s3 ls "s3://$BUCKET/$3")" ]; then
      echo "s3://$BUCKET/$3 already holds a published version; versions are never rewritten" >&2
      exit 1
    fi
    for f in $FILES; do
      if [ -f "$2/$f" ]; then
        s3 cp --only-show-errors "$2/$f" "s3://$BUCKET/$3$f"
      fi
    done ;;
  get-manifest)
    if ! err=$(s3 cp --only-show-errors "s3://$BUCKET/manifest.json" "$2" 2>&1); then
      rm -f "$2"
      if [[ "$err" == *"(404)"* || "$err" == *NoSuchKey* || "$err" == *"Not Found"* ]]; then
        echo "no manifest yet" >&2
      else
        echo "$err" >&2
        exit 1
      fi
    fi ;;
  put-manifest)
    s3 cp --only-show-errors "$2" "s3://$BUCKET/manifest.json" --content-type application/json --cache-control no-cache ;;
  list)
    # exit 1 with nothing on stderr is how the CLI says "no objects"; anything on stderr is a real failure
    errfile=$(mktemp)
    listing=$(s3 ls "s3://$BUCKET/packs/" --recursive 2> "$errfile") || [ ! -s "$errfile" ] || {
      cat "$errfile" >&2; echo "listing the bucket failed" >&2; exit 1; }
    python3 - "$listing" <<'PY'
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
    s3 rm --only-show-errors "s3://$BUCKET/$2" --recursive ;;
  *) sed -n 2,10p "$0" >&2; exit 2 ;;
esac
