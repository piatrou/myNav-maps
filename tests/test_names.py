from mapspack.config import load_countries
from mapspack.names import display_name, normalize, search_names

LEMESOS_CAPS = "\u039b\u0395\u039c\u0395\u03a3\u038c\u03a3"  # Greek, upper case, with tonos
LEMESOS = "\u039b\u03b5\u03bc\u03b5\u03c3\u03cc\u03c2"
MALADZECHNA = "\u041c\u0430\u043b\u0430\u0434\u0437\u0435\u0447\u043d\u0430"  # Belarusian Cyrillic
PACHNA = "\u03a0\u03ac\u03c7\u03bd\u03b1"


def test_normalize_folds_scripts_accents_case():
    assert normalize(LEMESOS_CAPS) == normalize("Lémesos") == "lemesos"
    assert normalize(MALADZECHNA) == "maladzecna"
    assert normalize("  Agios   Nikolaos ") == "agios nikolaos"


def test_display_prefers_english_keeps_original():
    assert display_name({"name": LEMESOS, "name:en": "Limassol"}) == ("Limassol", LEMESOS)
    assert display_name({"name": PACHNA}) == ("Pachna", PACHNA)
    assert display_name({"name": "Pyla"}) == ("Pyla", None)


def test_search_names_collects_all_variants():
    got = search_names({"name": LEMESOS, "name:en": "Limassol", "alt_name": "Lemesos;Limasol"})
    assert {LEMESOS, "Limassol", "Lemesos", "Limasol"} <= set(got)


def test_countries_yaml_loads():
    countries, place_details = load_countries()
    assert [c.id for c in countries] == ["cyprus", "greece", "north-carolina", "tennessee"]
    assert countries[0].drives_on_left and countries[0].zones[0].relation == 2514541
    assert place_details is True
