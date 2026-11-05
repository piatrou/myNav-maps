"""Turn lanes per way (Valhalla's API does not return them) -> lanes.json, the format the app's LaneTable reads.

Per way: turn:lanes for each direction plus the way's first and last node, so the app can tell which way it is
ridden. OSM lists lanes left to right in the direction of travel, also where traffic keeps left.
"""

import json
from pathlib import Path

import osmium


class _Handler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.ways: dict[int, dict] = {}

    def way(self, w):
        t = w.tags
        oneway = t.get("oneway") in ("yes", "1")
        fwd = t.get("turn:lanes:forward") or (t.get("turn:lanes") if oneway or "turn:lanes:backward" not in t else None)
        bwd = t.get("turn:lanes:backward")
        if not (fwd or bwd) or not w.nodes[0].location.valid() or not w.nodes[-1].location.valid():
            return
        a, b = w.nodes[0].location, w.nodes[-1].location
        self.ways[w.id] = {"fwd": fwd, "bwd": bwd, "first": [a.lat, a.lon], "last": [b.lat, b.lon]}


def build(pbf: Path, out: Path) -> int:
    """Write lanes.json; the number of ways with turn lanes."""
    h = _Handler()
    h.apply_file(str(pbf), locations=True)
    Path(out).write_text(json.dumps(h.ways))
    return len(h.ways)
