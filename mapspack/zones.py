"""Restricted zones -> zones.json: areas a route must never enter silently (the north of Cyprus beyond the Green
Line: passport and separate insurance). Valhalla routes through the checkpoints without a word, so the app checks
the route line against these polygons itself.

Rings are simplified to ~20 m (topology kept): plenty for a warning, a few KB instead of megabytes. Outer and inner
rings are mixed; even-odd tells inside.
"""

import json
from pathlib import Path

import osmium
import shapely.wkb
from shapely.geometry import MultiPolygon, Polygon

from .config import ZoneSpec

TOLERANCE = 0.0002  # degrees, ~20 m


class ZoneMissing(Exception):
    """A configured zone relation is not in the extract or does not close: never publish a pack without it."""

    def __init__(self, relation: int):
        super().__init__(f"zone relation {relation} not found or not closed in the extract")
        self.relation = relation


class _Handler(osmium.SimpleHandler):
    def __init__(self, wanted: set[int]):
        super().__init__()
        self.wanted = wanted
        self.wkb = osmium.geom.WKBFactory()
        self.shapes: dict[int, object] = {}

    def area(self, a):
        if not a.from_way() and a.orig_id() in self.wanted:
            try:
                self.shapes[a.orig_id()] = shapely.wkb.loads(self.wkb.create_multipolygon(a), hex=True)
            except RuntimeError:  # rings that do not close: left out, so build() names the relation
                pass


def rings(shape) -> list[list[float]]:
    """Flat [lat0, lon0, lat1, lon1, ...] per ring, closing point dropped, 5 decimals."""
    out = []
    for p in shape.geoms if isinstance(shape, MultiPolygon) else [shape]:
        assert isinstance(p, Polygon)
        for ring in [p.exterior, *p.interiors]:
            out.append([round(v, 5) for lon, lat in ring.coords[:-1] for v in (lat, lon)])
    return out


def build(pbf: Path, specs: list[ZoneSpec], out: Path) -> int:
    """Write zones.json when the country has zones; the number written. Raises ZoneMissing."""
    if not specs:
        return 0
    h = _Handler({s.relation for s in specs})
    h.apply_file(str(pbf), locations=True)
    zones = []
    for s in specs:
        if s.relation not in h.shapes:
            raise ZoneMissing(s.relation)
        simple = h.shapes[s.relation].simplify(TOLERANCE, preserve_topology=True)
        zones.append({"id": s.id, "name": s.name, "warning": s.warning, "source": f"OSM relation {s.relation}",
                      "rings": rings(simple)})
    Path(out).write_text(json.dumps({"zones": zones}, ensure_ascii=False, separators=(",", ":")))
    return len(zones)
