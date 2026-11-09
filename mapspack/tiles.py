"""A block's Valhalla tiles split per member: one graph built over the merged extracts, each member's pack holding
the tiles its outline touches. Tiles of one build share graph ids, so the app can use any members' tiles together."""

import io
import tarfile
from pathlib import Path, PurePosixPath

from shapely.geometry import Polygon, box

SIZES = {0: 4.0, 1: 1.0, 2: 0.25}  # degrees per tile side, per hierarchy level


def tile_box(name: str) -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat) of a tile by its path in the tar, e.g. "2/000/721/824.gph"."""
    p = PurePosixPath(name)
    if p.suffix != ".gph" or len(p.parts) < 2:
        raise ValueError(f"not a tile: {name}")
    size = SIZES[int(p.parts[0])]
    tile = int("".join(p.parts[1:])[:-len(".gph")])
    row, col = divmod(tile, int(360 / size))
    lat, lon = -90 + row * size, -180 + col * size
    return lon, lat, lon + size, lat + size


def _polygons(rings: list[list[float]]) -> list[Polygon]:
    return [Polygon(list(zip(r[1::2], r[0::2]))) for r in rings]  # flat lat, lon -> (lon, lat)


def split(tar: Path, members: dict[str, tuple[list[list[float]], Path]]) -> dict[str, int]:
    """Writes <out dir>/valhalla_tiles.tar per member (outline as flat lat, lon rings; holes ignored, so a border
    tile is never lost) with every tile whose box meets the outline. Returns tiles per member. An extract keeps whole
    ways, so the graph reaches past the outlines: a tile no outline meets goes to the nearest member, keeping the
    graph whole."""
    shapes = {m: _polygons(rings) for m, (rings, _) in members.items()}
    outs = {}
    for m, (_, d) in members.items():
        Path(d).mkdir(parents=True, exist_ok=True)
        outs[m] = tarfile.open(Path(d) / "valhalla_tiles.tar", "w", format=tarfile.USTAR_FORMAT)
    counts = dict.fromkeys(members, 0)
    try:
        with tarfile.open(tar) as src:
            for info in src:
                if not info.isfile() or not info.name.endswith(".gph"):
                    continue
                b = box(*tile_box(info.name))
                hit = [m for m, polys in shapes.items() if any(p.intersects(b) for p in polys)]
                if not hit:
                    hit = [min(shapes, key=lambda m: min(p.distance(b) for p in shapes[m]))]
                data = src.extractfile(info).read()
                for m in hit:
                    i = tarfile.TarInfo(info.name)
                    i.size, i.mtime = len(data), info.mtime
                    outs[m].addfile(i, io.BytesIO(data))
                    counts[m] += 1
    finally:
        for t in outs.values():
            t.close()
    return counts
