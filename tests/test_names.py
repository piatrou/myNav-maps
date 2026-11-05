from mapspack.config import load_countries
from mapspack.names import display_name, normalize, search_names

LEMESOS_CAPS = "ΛΕΜΕΣΌΣ"  # Greek, upper case, with tonos
LEMESOS = "Λεμεσός"
MALADZECHNA = "Маладзечна"  # Belarusian Cyrillic
PACHNA = "Πάχνα"


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
    assert [c.id for c in countries] == ["cyprus", "greece", "belarus"]
    assert countries[0].drives_on_left and countries[0].zones[0].relation == 2514541
    assert place_details is True
