"""Offline search -> search.sqlite: settlements, streets, places and street addresses, findable by any spelling.

Every name variant (original script, English, Russian, Belarusian, alt and old names, transliteration) is indexed in
its normalized form (names.normalize), in an FTS5 trigram table for "contains" matches and a plain index for one- or
two-letter prefixes (trigrams need three). The app runs the same query as `query` below; `nearest` is "what is here".
"""

import json
import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import osmium
from shapely import STRtree
from shapely.geometry import Point

from .landmarks import ROAD_FURNITURE, classify
from .names import ICU_TRANSFORM, display_name, latin, normalize, search_names

SCHEMA = """
CREATE TABLE place(id INTEGER PRIMARY KEY, osm TEXT NOT NULL, kind TEXT NOT NULL, rank INTEGER NOT NULL,
                   lat REAL NOT NULL, lon REAL NOT NULL, name TEXT NOT NULL, original TEXT,
                   street TEXT, housenumber TEXT, city TEXT, details TEXT);
CREATE TABLE place_name(place INTEGER NOT NULL, norm TEXT NOT NULL);
CREATE INDEX place_name_norm ON place_name(norm);
CREATE VIRTUAL TABLE place_fts USING fts5(norm, content='place_name', content_rowid='rowid', tokenize='trigram');
CREATE VIRTUAL TABLE place_rtree USING rtree(id, min_lat, max_lat, min_lon, max_lon);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
"""
SETTLEMENTS = {"city", "town", "village", "hamlet", "suburb"}
RANK = {"settlement": 0, "street": 1, "poi": 2, "address": 3}
CITY_RADIUS = 0.1  # degrees, ~10 km: an address without addr:city belongs to the nearest settlement within it
NEAR_BOX = 0.002  # degrees, ~200 m around a tapped point
DETAIL_KEYS = {"opening_hours": ("opening_hours",), "phone": ("phone", "contact:phone"),
               "website": ("website", "contact:website"), "cuisine": ("cuisine",)}


def _poi_kind(tags) -> str | None:
    if tags.get("tourism") == "viewpoint":
        return "viewpoint"
    if tags.get("mountain_pass") == "yes":
        return "mountain_pass"
    if tags.get("natural") == "peak":
        return "peak"
    return classify(tags)


class _Handler(osmium.SimpleHandler):
    def __init__(self, details: bool):
        super().__init__()
        self.details = details
        self.settlements: list[dict] = []
        self.streets: dict[str, dict] = {}  # by display name: points and name variants, split by settlement later
        self.pois: list[dict] = []
        self.addresses: list[dict] = []

    def _object(self, osm: str, tags, lat: float, lon: float, is_node: bool):
        if tags.get("place") in SETTLEMENTS and tags.get("name") and is_node:
            self.settlements.append(self._named(osm, "settlement", tags, lat, lon))
            return
        if tags.get("addr:housenumber") and tags.get("addr:street"):
            street = tags["addr:street"]
            shown = f'{display_name({"name": street})[0]} {tags["addr:housenumber"]}'
            self.addresses.append({"osm": osm, "kind": "address", "lat": lat, "lon": lon, "name": shown,
                                   "original": f'{street} {tags["addr:housenumber"]}' if latin(street) != street else None,
                                   "street": street, "housenumber": tags["addr:housenumber"],
                                   "city": tags.get("addr:city"),
                                   "names": [f'{v} {tags["addr:housenumber"]}' for v in search_names({"name": street})]})
        if tags.get("name") and (kind := _poi_kind(tags)) and kind not in ROAD_FURNITURE:
            row = self._named(osm, kind, tags, lat, lon)
            if self.details:
                found = {k: next((tags[t] for t in keys if t in tags), None) for k, keys in DETAIL_KEYS.items()}
                kept = {k: v for k, v in found.items() if v}
                row["details"] = json.dumps(kept, ensure_ascii=False) if kept else None
            self.pois.append(row)

    @staticmethod
    def _named(osm: str, kind: str, tags, lat: float, lon: float) -> dict:
        shown, original = display_name(dict(tags))
        return {"osm": osm, "kind": kind, "lat": lat, "lon": lon, "name": shown, "original": original,
                "names": search_names(dict(tags))}

    def node(self, n):
        if n.tags and n.location.valid():
            self._object(f"N{n.id}", n.tags, n.location.lat, n.location.lon, True)

    def way(self, w):
        pts = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        if not pts or not w.tags:
            return
        lat, lon = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        t = w.tags
        if t.get("highway") and t.get("name"):
            s = self.streets.setdefault(t["name"], {"osm": f"W{w.id}", "tags": dict(t), "points": []})
            s["points"].append((lat, lon))
            return
        self._object(f"W{w.id}", t, lat, lon, False)


def _streets(h: _Handler, near) -> list[dict]:
    """One row per street name per settlement: the parts of a long street meet in one place."""
    rows = []
    for name, s in h.streets.items():
        groups: dict[str | None, list] = {}
        for lat, lon in s["points"]:
            groups.setdefault(near(lat, lon), []).append((lat, lon))
        for city, pts in groups.items():
            row = _Handler._named(s["osm"], "street", s["tags"], sum(p[0] for p in pts) / len(pts),
                                  sum(p[1] for p in pts) / len(pts))
            row["city"] = city
            rows.append(row)
    return rows


def build(pbf: Path, out: Path, place_details: bool) -> dict[str, int]:
    """Write search.sqlite; row counts per kind group."""
    if tuple(int(x) for x in sqlite3.sqlite_version.split(".")) < (3, 34):
        raise RuntimeError(f"SQLite {sqlite3.sqlite_version} has no trigram tokenizer (needs 3.34+)")
    h = _Handler(place_details)
    h.apply_file(str(pbf), locations=True)

    towns = h.settlements
    tree = STRtree([Point(t["lon"], t["lat"]) for t in towns]) if towns else None

    def near(lat: float, lon: float) -> str | None:
        if tree is None:
            return None
        i = tree.query_nearest(Point(lon, lat), max_distance=CITY_RADIUS)
        return towns[int(i[0])]["name"] if len(i) else None

    for row in h.addresses + h.pois:
        row["city"] = row.get("city") or near(row["lat"], row["lon"])
    groups = {"settlement": towns, "street": _streets(h, near), "poi": h.pois, "address": h.addresses}

    out = Path(out)
    out.unlink(missing_ok=True)
    db = sqlite3.connect(out)
    db.executescript(SCHEMA)
    for group, rows in groups.items():
        for r in rows:
            cur = db.execute(
                "INSERT INTO place(osm, kind, rank, lat, lon, name, original, street, housenumber, city, details)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (r["osm"], r["kind"], RANK[group], r["lat"], r["lon"], r["name"], r.get("original"), r.get("street"),
                 r.get("housenumber"), r.get("city"), r.get("details")))
            pid = cur.lastrowid
            norms = {normalize(n) for n in r["names"]} - {""}
            db.executemany("INSERT INTO place_name(place, norm) VALUES (?, ?)", [(pid, n) for n in sorted(norms)])
            db.execute("INSERT INTO place_rtree VALUES (?,?,?,?,?)", (pid, r["lat"], r["lat"], r["lon"], r["lon"]))
    db.execute("INSERT INTO place_fts(place_fts) VALUES ('rebuild')")
    db.executemany("INSERT INTO meta VALUES (?, ?)", [("schema", "1"), ("icu_transform", ICU_TRANSFORM),
                                                      ("built", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))])
    db.commit()
    db.execute("VACUUM")
    db.close()
    return {k: len(v) for k, v in groups.items()}


def _connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def query(db: Path, text: str, near: tuple[float, float] | None, limit: int = 8) -> list[sqlite3.Row]:
    """The reference search the app ports: contains-match (prefix under three letters), settlements first, then
    streets, places, addresses; a query ending in a house number puts addresses first. Nearer first within a kind;
    then by name."""
    q = normalize(text)
    if not q:
        return []
    if len(q) >= 3:
        match = "SELECT place_name.place AS pid FROM place_fts JOIN place_name ON place_name.rowid = place_fts.rowid " \
                "WHERE place_fts MATCH ?"
        arg = '"' + q.replace('"', '""') + '"'
    else:
        match = "SELECT place AS pid FROM place_name WHERE norm >= ? AND norm < ?"
        arg = None
    lat, lon = near if near else (0.0, 0.0)
    k = math.cos(math.radians(lat)) ** 2
    dist = "(p.lat - ?) * (p.lat - ?) + (p.lon - ?) * (p.lon - ?) * ?, " if near else ""
    rank = "p.kind != 'address', p.rank" if q.split()[-1][:1].isdigit() else "p.rank"
    sql = f"SELECT p.* FROM place p WHERE p.id IN ({match}) ORDER BY {rank}, {dist}p.name LIMIT ?"
    params: list = [arg] if arg is not None else [q, q + "￿"]
    if near:
        params += [lat, lat, lon, lon, k]
    with _connect(db) as c:
        return c.execute(sql, [*params, limit]).fetchall()


def nearest(db: Path, lat: float, lon: float) -> sqlite3.Row | None:
    """What is here: the nearest address within ~200 m, else the nearest street."""
    k = math.cos(math.radians(lat)) ** 2
    with _connect(db) as c:
        for kind in ("address", "street"):
            row = c.execute(
                "SELECT p.* FROM place_rtree r JOIN place p ON p.id = r.id"
                " WHERE r.min_lat >= ? AND r.max_lat <= ? AND r.min_lon >= ? AND r.max_lon <= ? AND p.kind = ?"
                " ORDER BY (p.lat - ?) * (p.lat - ?) + (p.lon - ?) * (p.lon - ?) * ? LIMIT 1",
                (lat - NEAR_BOX, lat + NEAR_BOX, lon - NEAR_BOX, lon + NEAR_BOX, kind, lat, lat, lon, lon, k)).fetchone()
            if row:
                return row
    return None
