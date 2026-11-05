import json

import pytest

from mapspack import zones
from mapspack.config import ZoneSpec
from mapspack.zones import ZoneMissing
from tests.osm import write_osm


def test_missing_zone_relation_fails(tmp_path):
    pbf = write_osm(tmp_path, nodes=[{"id": 1, "lat": 35.0, "lon": 33.0}])
    with pytest.raises(ZoneMissing, match="2514541"):
        zones.build(pbf, [ZoneSpec("cy-north", 2514541, "Northern Cyprus", "w")], tmp_path / "zones.json")


def test_no_specs_no_file(tmp_path):
    assert zones.build(write_osm(tmp_path, nodes=[]), [], tmp_path / "zones.json") == 0
    assert not (tmp_path / "zones.json").exists()


def test_zone_square(tmp_path):
    corners = [(35.0, 33.0), (35.0, 33.1), (35.1, 33.1), (35.1, 33.0)]
    pbf = write_osm(tmp_path, nodes=[{"id": i + 1, "lat": la, "lon": lo} for i, (la, lo) in enumerate(corners)],
                    ways=[{"id": 50, "nodes": [1, 2, 3, 4, 1]}],
                    relations=[{"id": 99, "members": [("way", 50, "outer")],
                                "tags": {"type": "multipolygon", "name": "Square"}}])
    spec = ZoneSpec("sq", 99, "Square zone", "Careful.")
    assert zones.build(pbf, [spec], tmp_path / "zones.json") == 1
    z = json.loads((tmp_path / "zones.json").read_text())["zones"]
    assert len(z) == 1 and (z[0]["id"], z[0]["name"], z[0]["warning"]) == ("sq", "Square zone", "Careful.")
    assert len(z[0]["rings"]) == 1 and len(z[0]["rings"][0]) == 8


def test_open_ring_names_the_relation(tmp_path):
    corners = [(35.0, 33.0), (35.0, 33.1), (35.1, 33.1), (35.1, 33.0)]
    pbf = write_osm(tmp_path, nodes=[{"id": i + 1, "lat": la, "lon": lo} for i, (la, lo) in enumerate(corners)],
                    ways=[{"id": 50, "nodes": [1, 2, 3, 4]}],
                    relations=[{"id": 99, "members": [("way", 50, "outer")], "tags": {"type": "multipolygon"}}])
    with pytest.raises(ZoneMissing, match="99"):
        zones.build(pbf, [ZoneSpec("sq", 99, "Square zone", "Careful.")], tmp_path / "zones.json")
