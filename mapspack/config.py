"""Country list and brand table: the per-country facts live in YAML, not in code."""

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ZoneSpec:
    """A restricted area the app must warn about before a route enters it."""

    id: str
    relation: int
    name: str
    warning: str


@dataclass(frozen=True)
class Country:
    """One pack: a Geofabrik extract and what the app needs to know about it."""

    id: str
    name: str
    geofabrik: str
    drives_on_left: bool
    zones: list[ZoneSpec]
    #: Countries sharing a block are built as one routing graph, so routes run across them
    block: str | None = None


def load_countries(path: Path = ROOT / "countries.yaml") -> tuple[list[Country], bool]:
    """(countries, place_details)."""
    data = yaml.safe_load(Path(path).read_text())
    countries = [
        Country(c["id"], c["name"], c["geofabrik"], bool(c["drives_on_left"]),
                [ZoneSpec(z["id"], int(z["relation"]), z["name"], z["warning"]) for z in c.get("zones") or []],
                c.get("block"))
        for c in data["countries"]
    ]
    return countries, bool(data.get("place_details", False))


def blocks(countries: list[Country]) -> dict[str, list[Country]]:
    """Block id -> members in list order; a country without a block is a block of one under its own id."""
    ids = {c.id for c in countries}
    out: dict[str, list[Country]] = {}
    for c in countries:
        if c.block and c.block in ids:
            raise ValueError(f"block {c.block!r} has the id of a country")
        out.setdefault(c.block or c.id, []).append(c)
    return out


def load_brands(path: Path = ROOT / "brands.yaml") -> dict[str, str]:
    """OSM brand -> spoken English brand ("" = say only the noun)."""
    return {str(k): str(v) for k, v in (yaml.safe_load(Path(path).read_text()) or {}).items()}
