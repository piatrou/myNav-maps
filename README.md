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

## License

Map data © OpenStreetMap contributors, available under the
[Open Database License](https://www.openstreetmap.org/copyright). Elevation: Tilezen joerd (SRTM and others).
