import json

from mapspack import landmarks
from mapspack.landmarks import spoken_brand
from tests.osm import write_osm

ALPHAMEGA = "ΆλφαΜέγα"
EVROOPT = "Евроопт"
SOSEDI = "Сосedi"  # mixed Cyrillic and Latin


def test_spoken_brand_order():
    table = {ALPHAMEGA: "AlphaMega"}
    assert spoken_brand({"brand": ALPHAMEGA}, table) == "AlphaMega"
    assert spoken_brand({"brand": EVROOPT, "brand:en": "Euroopt"}, table) == "Euroopt"
    assert spoken_brand({"brand": "Lidl"}, table) == "Lidl"
    assert spoken_brand({"brand": SOSEDI}, {}) != ""
    assert spoken_brand({}, table) == ""


def test_landmarks_compact_format(tmp_path):
    pbf = write_osm(tmp_path, nodes=[
        {"id": 1, "lat": 35.1, "lon": 33.2, "tags": {"amenity": "fuel", "brand": "EKO"}},
        {"id": 2, "lat": 35.2, "lon": 33.3, "tags": {"amenity": "place_of_worship", "religion": "muslim"}}])
    out = tmp_path / "landmarks.json"
    assert landmarks.build(pbf, out, {"EKO": "Eko"}) == 2
    d = json.loads(out.read_text())
    assert d["kinds"] == ["fuel", "place_of_worship"] and d["lat"] == [3510000, 3520000]
    assert d["brand"] == {"0": "Eko"} and d["muslim"] == [1] and d["sal"] == "hh"
