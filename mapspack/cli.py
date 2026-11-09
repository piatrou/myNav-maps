"""Entry points for the workflow: python -m mapspack <tables|entry|version|plan|split|merge|retired> ..."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import osmium

from . import landmarks, lanes, manifest, outline, search, tiles, zones
from .config import load_brands, load_countries, plan


def _country(country_id: str):
    countries, place_details = load_countries()
    for c in countries:
        if c.id == country_id:
            return c, place_details
    sys.exit(f"unknown country {country_id!r}; see countries.yaml")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pbf_version(pbf: Path) -> str:
    """The extract's data date (Geofabrik writes the replication timestamp into the header), else today (UTC)."""
    stamp = osmium.io.Reader(str(pbf), osmium.osm.osm_entity_bits.NOTHING).header().get(
        "osmosis_replication_timestamp")
    return stamp[:10] if stamp else datetime.now(UTC).strftime("%Y-%m-%d")


def tables(args):
    c, place_details = _country(args.country)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    print("lanes:", lanes.build(args.pbf, out / "lanes.json"))
    print("landmarks:", landmarks.build(args.pbf, out / "landmarks.json", load_brands()))
    print("zones:", zones.build(args.pbf, c.zones, out / "zones.json"))
    print("search:", search.build(args.pbf, out / "search.sqlite", place_details))


def entry(args):
    c, _ = _country(args.country)
    version = args.version or pbf_version(args.pbf)
    prefix = f"packs/{c.id}/{version}/"
    e = manifest.pack_entry(c, version, Path(args.packdir), prefix, outline.from_poly(outline.fetch(c.geofabrik)),
                            _now())
    json.dump(e, sys.stdout, ensure_ascii=False)


def version(args):
    print(min(pbf_version(p) for p in args.pbfs))


def plan_blocks(args):
    print(json.dumps(plan([w.strip() for w in args.wanted.split(",") if w.strip()])))


def split(args):
    members = {}
    for spec in args.members:
        cid, _, packdir = spec.partition("=")
        c, _ = _country(cid)
        members[c.id] = (outline.from_poly(outline.fetch(c.geofabrik), tolerance=0), Path(packdir))
    for cid, n in tiles.split(args.tar, members).items():
        print(f"{cid}: {n} tiles")


def merge(args):
    old = None if args.old == "-" or not Path(args.old).exists() else json.loads(Path(args.old).read_text())
    built = [json.loads(p.read_text()) for p in sorted(Path(args.entries).rglob("*.json"))]
    json.dump(manifest.merge(old, built, _now()), sys.stdout, ensure_ascii=False)


def retired(args):
    current = json.loads(Path(args.manifest).read_text())
    listing = json.loads(Path(args.listing).read_text())
    for prefix in manifest.retired(listing, current, datetime.now(UTC)):
        print(prefix)


def main(argv=None):
    p = argparse.ArgumentParser(prog="mapspack")
    sub = p.add_subparsers(required=True)
    s = sub.add_parser("tables", help="lanes, landmarks, zones, search for one country")
    s.add_argument("country"); s.add_argument("pbf", type=Path); s.add_argument("outdir")
    s.set_defaults(fn=tables)
    s = sub.add_parser("entry", help="manifest entry of a built pack (JSON on stdout)")
    s.add_argument("country"); s.add_argument("pbf", type=Path); s.add_argument("packdir")
    s.add_argument("--version", help="the block's version instead of the extract's date")
    s.set_defaults(fn=entry)
    s = sub.add_parser("version", help="the oldest data date of the extracts: a block's version")
    s.add_argument("pbfs", type=Path, nargs="+")
    s.set_defaults(fn=version)
    s = sub.add_parser("plan", help="blocks to build for comma-separated country ids (empty = all), JSON")
    s.add_argument("wanted", nargs="?", default="")
    s.set_defaults(fn=plan_blocks)
    s = sub.add_parser("split", help="a block's valhalla_tiles.tar split per member: <id>=<packdir> ...")
    s.add_argument("tar", type=Path); s.add_argument("members", nargs="+")
    s.set_defaults(fn=split)
    s = sub.add_parser("merge", help="new manifest from the old one and built entries (JSON on stdout)")
    s.add_argument("old"); s.add_argument("entries")
    s.set_defaults(fn=merge)
    s = sub.add_parser("retired", help="version prefixes to delete, one per line")
    s.add_argument("manifest"); s.add_argument("listing")
    s.set_defaults(fn=retired)
    args = p.parse_args(argv)
    args.fn(args)
