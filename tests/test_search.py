import json

import pytest

from mapspack import search
from mapspack.search import nearest, query
from tests.osm import write_osm

LEMESOS = "Λεμεσός"
LEMESOS_CAPS = "ΛΕΜΕΣΌΣ"
LEMESOS_CYRILLIC = "Лемесос"
ATHINON = "Οδός Αθηνών"
ZINON = "Ζήνων"


@pytest.fixture
def fixture_pbf(tmp_path):
    return write_osm(tmp_path, nodes=[
        {"id": 1, "lat": 34.68, "lon": 33.04, "tags": {"place": "city", "name": LEMESOS, "name:en": "Limassol"}},
        {"id": 2, "lat": 34.6800, "lon": 33.0400}, {"id": 3, "lat": 34.6810, "lon": 33.0410},
        {"id": 4, "lat": 34.6801, "lon": 33.0401, "tags": {"addr:street": ATHINON, "addr:housenumber": "12"}},
        {"id": 5, "lat": 34.6850, "lon": 33.0450, "tags": {"amenity": "cafe", "name": ZINON,
                                                          "opening_hours": "Mo-Su 08:00-22:00"}},
        {"id": 6, "lat": 34.72, "lon": 33.15, "tags": {"place": "village", "name": "Agios Tychonas"}},
        {"id": 7, "lat": 35.00, "lon": 32.50, "tags": {"place": "village", "name": "Agios Ioannis"}},
        {"id": 8, "lat": 34.6802, "lon": 33.0402, "tags": {"amenity": "cafe", "name": "Athinon 123 Cafe"}},
        {"id": 9, "lat": 34.6803, "lon": 33.0403, "tags": {"highway": "bus_stop", "name": "Athinon 12 stop"}},
    ], ways=[{"id": 20, "nodes": [2, 3], "tags": {"highway": "residential", "name": ATHINON}}])


@pytest.fixture
def db(tmp_path, fixture_pbf):
    out = tmp_path / "search.sqlite"
    search.build(fixture_pbf, out, place_details=True)
    return out


def test_finds_by_any_spelling(db):
    for q in ("limassol", "lemesos", LEMESOS_CAPS, LEMESOS_CYRILLIC):
        assert query(db, q, None)[0]["name"] == "Limassol", q


def test_original_kept(db):
    assert query(db, "limassol", None)[0]["original"] == LEMESOS


def test_settlement_ranks_before_street_and_address(db):
    kinds = [r["kind"] for r in query(db, "athin", None)]
    assert kinds.index("street") < kinds.index("address")


def test_short_query_uses_prefix(db):
    assert any(r["name"] == "Limassol" for r in query(db, "Li", None))


def test_address_gets_nearest_city(db):
    row = next(r for r in query(db, "athinon 12", None) if r["kind"] == "address")
    assert row["city"] == "Limassol" and row["housenumber"] == "12"


def test_nearer_first_within_a_rank(db):
    assert query(db, "agios", (34.72, 33.15))[0]["name"] == "Agios Tychonas"
    assert query(db, "agios", (35.0, 32.5))[0]["name"] == "Agios Ioannis"


def test_details_only_when_enabled(tmp_path, fixture_pbf):
    on, off = tmp_path / "on.sqlite", tmp_path / "off.sqlite"
    search.build(fixture_pbf, on, True)
    search.build(fixture_pbf, off, False)
    assert json.loads(query(on, "zinon", None)[0]["details"])["opening_hours"] == "Mo-Su 08:00-22:00"
    assert query(off, "zinon", None)[0]["details"] is None


def test_nearest_is_the_address(db):
    assert nearest(db, 34.6801, 33.0401)["kind"] == "address"


def test_nearest_nothing_far_away(db):
    assert nearest(db, 40.0, 20.0) is None


def test_house_number_query_puts_addresses_first(db):
    assert query(db, "athinon 12", None)[0]["kind"] == "address"


def test_bus_stops_are_not_searchable(db):
    assert all(r["kind"] != "bus_stop" for r in query(db, "stop", None))


def test_place_gets_nearest_city(db):
    assert query(db, "zinon", None)[0]["city"] == "Limassol"
