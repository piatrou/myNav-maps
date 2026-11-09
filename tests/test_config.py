import pytest

from mapspack.config import blocks, load_countries


def test_states_share_a_block():
    countries, _ = load_countries()
    assert {c.id: c.block for c in countries} == {"cyprus": None, "greece": None,
                                                   "north-carolina": "us-appalachia", "tennessee": "us-appalachia"}


def test_blocks_group_members_and_keep_standalone_alone():
    countries, _ = load_countries()
    assert {k: [c.id for c in v] for k, v in blocks(countries).items()} == {
        "cyprus": ["cyprus"], "greece": ["greece"], "us-appalachia": ["north-carolina", "tennessee"]}


def test_block_id_must_not_clash_with_a_country(tmp_path):
    # a block named like a country would merge a standalone pack into it
    (tmp_path / "c.yaml").write_text("countries:\n"
                                     "  - {id: a, name: A, geofabrik: x/a, drives_on_left: false, block: b}\n"
                                     "  - {id: b, name: B, geofabrik: x/b, drives_on_left: false}\n")
    with pytest.raises(ValueError):
        blocks(load_countries(tmp_path / "c.yaml")[0])
