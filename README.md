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

Measured build cost (Valhalla 3.9.1, 4 threads, with elevation):

| Country | `.osm.pbf` | Build | Peak heap | `tiles.tar` |
|---|---|---|---|---|
| Cyprus | 38 MB | 10 s | 0.5 GB | 65 MB |
| Greece | 343 MB | 85 s | 1.8 GB | 518 MB |
| France | 4.9 GB | 16 min | 4.4 GB | 4 GB |

## License

Map data © OpenStreetMap contributors, available under the
[Open Database License](https://www.openstreetmap.org/copyright). Elevation: Tilezen joerd (SRTM and others).
