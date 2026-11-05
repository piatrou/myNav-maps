import hashlib
from datetime import UTC, datetime

from mapspack.config import load_countries
from mapspack.manifest import merge, pack_entry, retired

CYPRUS = load_countries()[0][0]


def test_merge_keeps_countries_not_rebuilt():
    old = {"schema": 1, "packs": [{"id": "cyprus", "version": "2026-11-01"}, {"id": "greece", "version": "2026-11-01"}]}
    new = merge(old, [{"id": "greece", "version": "2026-12-01"}], "2026-12-02T00:00:00Z")
    assert [(p["id"], p["version"]) for p in new["packs"]] == [("cyprus", "2026-11-01"), ("greece", "2026-12-01")]
    assert new["generated"] == "2026-12-02T00:00:00Z" and new["schema"] == 1


def test_merge_orders_by_country_list_and_starts_empty():
    new = merge(None, [{"id": "belarus", "version": "b"}, {"id": "cyprus", "version": "c"}], "t")
    assert [p["id"] for p in new["packs"]] == ["cyprus", "belarus"]


def test_retired_waits_seven_days():
    cur = {"packs": [{"id": "cyprus", "version": "2026-12-01", "published": "2026-12-02T00:00:00Z"}]}
    listing = {"cyprus": ["2026-11-01", "2026-12-01"]}
    assert retired(listing, cur, datetime(2026, 12, 8, tzinfo=UTC)) == []
    assert retired(listing, cur, datetime(2026, 12, 10, tzinfo=UTC)) == ["packs/cyprus/2026-11-01/"]


def test_retired_never_touches_unknown_countries():
    cur = {"packs": [{"id": "cyprus", "version": "v2", "published": "2026-01-01T00:00:00Z"}]}
    assert retired({"poland": ["v1"]}, cur, datetime(2026, 12, 10, tzinfo=UTC)) == []


def test_entry_hashes_every_file(tmp_path):
    (tmp_path / "lanes.json").write_text("{}")
    e = pack_entry(CYPRUS, "2026-12-01", tmp_path, "packs/cyprus/2026-12-01/", [[0, 0]], "2026-12-02T00:00:00Z")
    f = e["files"][0]
    assert f["name"] == "lanes.json" and f["size"] == 2 and f["sha256"] == hashlib.sha256(b"{}").hexdigest()
    assert f["path"] == "packs/cyprus/2026-12-01/lanes.json"
    assert e["valhalla"] == "3.9.1" and e["drivesOnLeft"] is True and e["name"] == "Cyprus"


def test_version_falls_back_to_today_without_header_stamp(tmp_path):
    from mapspack.cli import pbf_version
    from tests.osm import write_osm
    assert pbf_version(write_osm(tmp_path, nodes=[])) == datetime.now(UTC).strftime("%Y-%m-%d")
