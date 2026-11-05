"""A country's outline for the manifest: which pack covers a point, before the pack is downloaded."""

import urllib.request

from shapely.geometry import LinearRing


def from_poly(text: str, tolerance: float = 0.01) -> list[list[float]]:
    """Geofabrik .poly (lon lat per line, sections ending in END, holes prefixed with !) -> flat [lat, lon, ...]
    rings, simplified by `tolerance` degrees (0.01 ~ 1 km: plenty to pick a country). Even-odd tells inside."""
    lines = [l.strip() for l in text.splitlines()][1:]  # first line is the file's name
    out, ring = [], None
    for line in lines:
        if not line:
            continue
        if ring is None:
            if line == "END":
                break
            ring = []
            continue
        if line == "END":
            pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
            if tolerance > 0 and len(pts) > 3:
                simple = LinearRing(pts).simplify(tolerance, preserve_topology=True)
                pts = list(simple.coords)[:-1]
            out.append([round(v, 5) for lon, lat in pts for v in (lat, lon)])
            ring = None
            continue
        lon, lat = (float(v) for v in line.split()[:2])
        ring.append((lon, lat))
    return out


def fetch(geofabrik: str) -> str:
    """The .poly of a Geofabrik extract, e.g. "europe/cyprus"."""
    with urllib.request.urlopen(f"https://download.geofabrik.de/{geofabrik}.poly", timeout=60) as r:
        return r.read().decode()
