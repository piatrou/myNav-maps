"""manifest.json: what the app downloads. One entry per country; a version path is never rewritten, the manifest is
switched last, so a client never sees a half-published pack."""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from .config import Country, load_countries

VALHALLA = "3.9.1"  # the Valhalla inside valhalla-mobile 0.6.4; the app refuses packs built for another one
PACK_FILES = ("valhalla_tiles.tar", "lanes.json", "landmarks.json", "basemap.mbtiles", "search.sqlite", "zones.json")
KEEP_RETIRED = timedelta(days=7)  # downloads already running when the manifest switches can still finish


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class PackIncomplete(Exception):
    """A pack misses a file it must have: never publish a country without its map or its zones."""


def pack_entry(country: Country, version: str, packdir: Path, prefix: str, outline: list[list[float]],
               published: str) -> dict:
    """The manifest entry of a built pack: every pack file with size and sha256. zones.json exactly when the
    country has zones. Raises PackIncomplete."""
    names = [n for n in PACK_FILES if n != "zones.json" or country.zones]
    if missing := [n for n in names if not (packdir / n).exists()]:
        raise PackIncomplete(f"{country.id}: missing {', '.join(missing)}")
    files = [{"name": n, "size": (packdir / n).stat().st_size, "sha256": _sha256(packdir / n), "path": prefix + n}
             for n in names]
    return {"id": country.id, "name": country.name, "version": version, "valhalla": VALHALLA,
            "drivesOnLeft": country.drives_on_left, "published": published, "outline": outline, "files": files}


def merge(old: dict | None, built: list[dict], now: str) -> dict:
    """The new manifest: entries of rebuilt countries replaced, the others kept as they were; countries no longer
    in countries.yaml dropped (their files in the bucket stay until removed by hand)."""
    packs = {p["id"]: p for p in (old or {}).get("packs", [])}
    packs.update({p["id"]: p for p in built})
    order = {c.id: i for i, c in enumerate(load_countries()[0])}
    return {"schema": 1, "generated": now,
            "packs": sorted((p for p in packs.values() if p["id"] in order), key=lambda p: order[p["id"]])}


def _time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def retired(listing: dict[str, list[str]], current: dict, now: datetime) -> list[str]:
    """Version prefixes to delete: not current, once the current one has been out for more than 7 days.
    Countries missing from the manifest are left alone."""
    out = []
    for p in current.get("packs", []):
        if now - _time(p["published"]) <= KEEP_RETIRED:
            continue
        out += [f"packs/{p['id']}/{v}/" for v in sorted(listing.get(p["id"], [])) if v != p["version"]]
    return out
