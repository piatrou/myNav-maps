from mapspack import outline


def test_poly_outline():
    poly = "cyprus\n1\n   33.0 35.0\n   34.0 35.0\n   34.0 36.0\n   33.0 36.0\nEND\nEND\n"
    assert outline.from_poly(poly) == [[35.0, 33.0, 35.0, 34.0, 36.0, 34.0, 36.0, 33.0]]


def test_poly_keeps_holes_as_rings():
    poly = ("x\n1\n 0 0\n 10 0\n 10 10\n 0 10\nEND\n!2\n 4 4\n 6 4\n 6 6\n 4 6\nEND\nEND\n")
    assert len(outline.from_poly(poly, tolerance=0)) == 2
