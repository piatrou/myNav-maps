# myNav-maps

Builds the offline country packs for the MyNav iOS app (motorcycle voice navigation) and publishes them to
Cloudflare R2. This repo holds only the build scripts and the GitHub Actions workflow; the packs themselves never
go into git.

A pack is one country (or a Geofabrik region for the big ones), built from the Geofabrik `.osm.pbf` extract:

- Valhalla routing tiles (`valhalla_tiles.tar`), built with the same Valhalla version the app embeds
  (valhalla-mobile 0.6.4 = Valhalla 3.9.1); a mismatch makes the app refuse the tiles;
- `lanes.json` and `landmarks.json` for the voice cues;
- an offline base map (`.mbtiles`, OpenMapTiles schema);
- a `manifest.json` entry: version, size, sha256.

Countries: [countries.yaml](countries.yaml) (Cyprus, Greece, Belarus). The app reads
`<R2_PUBLIC_URL>/manifest.json`: per country the version (the extract's date), Valhalla version, driving side,
outline, and every file with size and sha256 under an immutable `packs/<id>/<version>/` path.

## Build

GitHub Actions ([build.yml](.github/workflows/build.yml)) runs on the 2nd of every month, or by hand:

    gh workflow run build.yml -f countries=cyprus

GitHub turns off scheduled workflows in a public repo after 60 days without a commit. If the repo has been quiet,
check the Actions tab (re-enable the workflow) or run it by hand; the manifest's `generated` date shows how fresh
the packs are.

Locally (Docker; PyICU needs ICU: `brew install icu4c pkg-config`,
`export PKG_CONFIG_PATH=$(brew --prefix icu4c)/lib/pkgconfig`):

    uv sync && uv run pytest
    uv run python -m mapspack tables cyprus cyprus-latest.osm.pbf work/pack
    scripts/build_valhalla.sh cyprus-latest.osm.pbf work/pack
    scripts/build_basemap.sh cyprus-latest.osm.pbf work/pack

Measured Valhalla build cost (3.9.1, 4 threads, with elevation):

| Country | `.osm.pbf` | Build | Peak heap | `tiles.tar` |
|---|---|---|---|---|
| Cyprus | 38 MB | 10 s | 0.5 GB | 65 MB |
| Greece | 343 MB | 85 s | 1.8 GB | 518 MB |
| France (reference) | 4.9 GB | 16 min | 4.4 GB | 4 GB |

Measured packs, first Actions build (2026-11-05, extracts dated 2026-11-03, `place_details: true`), sizes in MB:

| Country | `.osm.pbf` | Tables | Valhalla | Base map | `valhalla_tiles.tar` | `basemap.mbtiles` | `search.sqlite` | `landmarks.json` | `lanes.json` | `zones.json` | Pack |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Cyprus | 38 | 1.2 min | 0.5 min | 1.2 min | 73.1 | 39.4 | 19.1 | 0.9 | 0.2 | 0.01 | 133 |
| Greece | 343 | 10.7 min | 2.9 min | 3.4 min | 579.1 | 383.0 | 110.3 | 5.6 | 1.3 | - | 1079 |
| Belarus | 352 | 12.3 min | 2.1 min | 3.4 min | 406.2 | 604.8 | 412.5 | 5.4 | 1.5 | - | 1430 |

All three: 2.64 GB of the 10 GB R2 free tier, so place details stay on. A monthly run keeps at most two versions
per country for 7 days (about 5.3 GB at peak). A whole job takes 25 min for Greece or Belarus (4 min of it freeing
disk on the runner).

## License

Map data © OpenStreetMap contributors, available under the
[Open Database License](https://www.openstreetmap.org/copyright). Elevation: Tilezen joerd (SRTM and others).
