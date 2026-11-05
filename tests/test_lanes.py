import json

from mapspack import lanes
from tests.osm import write_osm


def test_lanes_keep_app_format(tmp_path):
    pbf = write_osm(tmp_path, nodes=[{"id": 1, "lat": 35.0, "lon": 33.0}, {"id": 2, "lat": 35.001, "lon": 33.0}],
                    ways=[{"id": 10, "nodes": [1, 2], "tags": {"highway": "primary", "oneway": "yes",
                                                              "turn:lanes": "left|through"}}])
    out = tmp_path / "lanes.json"
    assert lanes.build(pbf, out) == 1
    assert json.loads(out.read_text()) == {"10": {"fwd": "left|through", "bwd": None,
                                                  "first": [35.0, 33.0], "last": [35.001, 33.0]}}


def test_way_without_lanes_is_skipped(tmp_path):
    pbf = write_osm(tmp_path, nodes=[{"id": 1, "lat": 35.0, "lon": 33.0}, {"id": 2, "lat": 35.001, "lon": 33.0}],
                    ways=[{"id": 10, "nodes": [1, 2], "tags": {"highway": "primary"}}])
    assert lanes.build(pbf, tmp_path / "lanes.json") == 0
