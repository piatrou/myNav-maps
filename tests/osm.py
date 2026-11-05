"""Tiny OSM XML fixtures that pyosmium reads like a real extract."""

from pathlib import Path
from xml.sax.saxutils import quoteattr


def _tags(tags: dict[str, str] | None) -> str:
    return "".join(f"<tag k={quoteattr(k)} v={quoteattr(v)}/>" for k, v in (tags or {}).items())


def write_osm(tmp_path: Path, nodes: list[dict], ways: list[dict] = (), relations: list[dict] = (),
              name: str = "fixture.osm") -> Path:
    """nodes: id, lat, lon, tags; ways: id, nodes, tags; relations: id, members [(type, ref, role)], tags."""
    meta = 'version="1" timestamp="2026-11-01T00:00:00Z"'
    parts = ['<?xml version="1.0" encoding="UTF-8"?><osm version="0.6" generator="test">']
    for n in nodes:
        parts.append(f'<node id="{n["id"]}" {meta} lat="{n["lat"]}" lon="{n["lon"]}">{_tags(n.get("tags"))}</node>')
    for w in ways:
        refs = "".join(f'<nd ref="{r}"/>' for r in w["nodes"])
        parts.append(f'<way id="{w["id"]}" {meta}>{refs}{_tags(w.get("tags"))}</way>')
    for r in relations:
        members = "".join(f'<member type="{t}" ref="{ref}" role="{role}"/>' for t, ref, role in r["members"])
        parts.append(f'<relation id="{r["id"]}" {meta}>{members}{_tags(r.get("tags"))}</relation>')
    parts.append("</osm>")
    path = Path(tmp_path) / name
    path.write_text("".join(parts), encoding="utf-8")
    return path
