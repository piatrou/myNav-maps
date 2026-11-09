import io
import tarfile

import pytest

from mapspack.tiles import split, tile_box


def test_tile_box_levels():
    assert tile_box("0/000/000.gph") == (-180, -90, -176, -86)
    assert tile_box("1/000/360.gph") == (-180, -89, -179, -88)
    assert tile_box("1/045/213.gph") == (33, 35, 34, 36)  # Cyprus
    assert tile_box("2/000/721/824.gph") == (-84.0, 35.25, -83.75, 35.5)  # Deals Gap
    with pytest.raises(ValueError):
        tile_box("index.bin")


def _tar(path, names):
    with tarfile.open(path, "w") as t:
        for n in names:
            data = n.encode()
            info = tarfile.TarInfo(n)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))


def _square(lat0, lat1, lon0, lon1):
    return [[lat0, lon0, lat0, lon1, lat1, lon1, lat1, lon0]]


def _names(path):
    with tarfile.open(path) as t:
        return {m.name for m in t.getmembers()}


ROW = ["2/000/721/822.gph", "2/000/721/823.gph", "2/000/721/824.gph", "2/000/721/825.gph"]  # lon -84.5 ... -83.5


def test_split_puts_border_tiles_in_both(tmp_path):
    _tar(tmp_path / "in.tar", ["index.bin"] + ROW)
    counts = split(tmp_path / "in.tar", {"west": (_square(35.3, 35.4, -84.45, -83.9), tmp_path / "west"),
                                         "east": (_square(35.3, 35.4, -84.1, -83.55), tmp_path / "east")})
    assert counts == {"west": 3, "east": 3}
    assert _names(tmp_path / "west" / "valhalla_tiles.tar") == set(ROW[:3])
    assert _names(tmp_path / "east" / "valhalla_tiles.tar") == set(ROW[1:])
    with tarfile.open(tmp_path / "west" / "valhalla_tiles.tar") as t:
        assert t.extractfile(ROW[0]).read() == ROW[0].encode()


def test_split_refuses_orphan_tiles(tmp_path):
    _tar(tmp_path / "in.tar", ROW)
    with pytest.raises(ValueError):
        split(tmp_path / "in.tar", {"west": (_square(35.3, 35.4, -84.45, -84.3), tmp_path / "west")})
