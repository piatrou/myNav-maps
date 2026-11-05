"""Objects a rider could see near a turn -> landmarks.json, the compact columnar format the app's LandmarkTable reads.

Everything visible from the road (shops, cafes, fuel, churches, schools, monuments) plus road furniture (zebra
crossings, STOP and give-way signs, bus stops, speed bumps), each with a salience guess. Every object is kept,
landmark or not: "the only cafe at the corner" needs the other cafes counted. Names are not shipped: only chain
brands are said, the way an English voice can read them.
"""

import json
import unicodedata
from pathlib import Path

import osmium

from .names import latin

HIGH = {"fuel", "place_of_worship", "supermarket", "hospital", "school", "university", "stadium", "hotel",
        "monument", "castle", "police", "fire_station", "townhall", "department_store", "mall", "car_dealer",
        "marketplace", "water_tower", "bus_station"}
MEDIUM = {"cafe", "restaurant", "fast_food", "pharmacy", "bank", "bar", "pub", "post_office", "kindergarten",
          "car_wash", "car_repair", "bakery", "museum", "memorial", "park", "convenience", "doityourself", "hardware",
          "playground", "parking", "shop", "stop", "give_way", "crossing", "speed_bump", "bus_stop"}
ROAD_FURNITURE = {"stop", "give_way", "crossing", "speed_bump", "bus_stop"}
AMENITIES = {"fuel", "place_of_worship", "hospital", "school", "university", "police", "fire_station", "townhall",
             "marketplace", "bus_station", "cafe", "restaurant", "fast_food", "pharmacy", "bank", "bar", "pub",
             "post_office", "kindergarten", "car_wash"}
SHOPS = {"supermarket", "department_store", "mall", "car", "convenience", "doityourself", "hardware", "bakery",
         "car_repair"}


def classify(tags) -> str | None:
    """The landmark kind of an OSM object, or None when a rider would not use it."""
    if any(k.startswith(("disused:", "abandoned:", "was:")) for k, _ in tags):
        return None
    hw, amenity, shop = tags.get("highway"), tags.get("amenity"), tags.get("shop")
    if hw in ("stop", "give_way", "bus_stop"):
        return hw
    if hw == "crossing" and tags.get("crossing") in ("zebra", "marked", "uncontrolled", "traffic_signals"):
        return "crossing"
    if tags.get("traffic_calming") in ("bump", "hump", "table"):
        return "speed_bump"
    if amenity in AMENITIES:
        return amenity
    if amenity == "parking" and tags.get("name"):
        return "parking"
    if shop in SHOPS:
        return {"car": "car_dealer"}.get(shop, shop)
    if shop:
        return "shop" if (tags.get("name") or tags.get("brand")) else None
    if tags.get("tourism") in ("hotel", "museum"):
        return tags["tourism"]
    if tags.get("historic") in ("monument", "memorial", "castle"):
        return tags["historic"]
    if tags.get("leisure") in ("park", "stadium", "playground") and tags.get("name"):
        return tags["leisure"]
    if tags.get("man_made") == "water_tower":
        return "water_tower"
    return None


def salience(kind: str, tags, is_building: bool) -> str:
    """h / m / l: big, long-lived, visible things first."""
    if kind in HIGH or (tags.get("brand") and kind in ("fast_food", "cafe", "convenience", "shop", "bank")):
        return "h"
    if kind in MEDIUM:
        return "m" if (tags.get("name") or kind in ROAD_FURNITURE or is_building) else "l"
    return "l"


def _is_latin(s: str) -> bool:
    return all(not c.isalpha() or unicodedata.name(c, "").startswith("LATIN") for c in s)


def spoken_brand(tags, brands: dict[str, str]) -> str:
    """The brand as an English voice says it: table > brand:en > a Latin brand > a short transliteration > ""."""
    brand = tags.get("brand")
    if not brand:
        return ""
    if brand in brands:
        return brands[brand]
    if en := tags.get("brand:en"):
        return en
    if _is_latin(brand):
        return brand
    spelled = latin(brand)
    return spelled if spelled and len(spelled.split()) <= 3 else ""


class _Handler(osmium.SimpleHandler):
    def __init__(self, brands: dict[str, str]):
        super().__init__()
        self.brands = brands
        self.rows: list[tuple] = []  # kind, lat, lon, sal, building, year, brand, muslim

    def _add(self, o, kind: str, lat: float, lon: float, building: bool):
        t = o.tags
        self.rows.append((kind, lat, lon, salience(kind, t, building), building,
                          o.timestamp.year if o.timestamp else 0, spoken_brand(t, self.brands),
                          t.get("religion") == "muslim"))

    def node(self, n):
        if (kind := classify(n.tags)) and n.location.valid():
            self._add(n, kind, n.location.lat, n.location.lon, False)

    def way(self, w):
        kind = classify(w.tags)
        if not kind or kind in ROAD_FURNITURE:
            return
        pts = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        if pts:
            self._add(w, kind, sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), True)


def build(pbf: Path, out: Path, brands: dict[str, str]) -> int:
    """Write landmarks.json; the number of objects."""
    h = _Handler(brands)
    h.apply_file(str(pbf), locations=True)
    kinds = sorted({r[0] for r in h.rows})
    code = {k: i for i, k in enumerate(kinds)}
    d = {"kinds": kinds, "lat": [round(r[1] * 1e5) for r in h.rows], "lon": [round(r[2] * 1e5) for r in h.rows],
         "kind": [code[r[0]] for r in h.rows], "sal": "".join(r[3] for r in h.rows),
         "bld": "".join("1" if r[4] else "0" for r in h.rows), "year": [r[5] for r in h.rows],
         "brand": {str(i): r[6] for i, r in enumerate(h.rows) if r[6]},
         "muslim": [i for i, r in enumerate(h.rows) if r[7]]}
    Path(out).write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    return len(h.rows)
