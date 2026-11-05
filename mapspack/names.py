"""One transliteration rule for the search index and the app: whatever script a name or a query is in, both are
folded to the same lower-case ASCII, so "lemesos" finds the Greek original and a Cyrillic query finds it too."""

import re

import icu

# Modern Greek romanization (UNGEGN, as on road signs: "Athinon", not the classical "Athenon"), then any other
# script. The app applies the same ICU transform to the rider's query (Foundation StringTransform); keep them identical.
LATIN = "Greek-Latin/UNGEGN; Any-Latin; Latin-ASCII"
ICU_TRANSFORM = LATIN + "; Lower"
_fold = icu.Transliterator.createInstance(ICU_TRANSFORM)
_latin = icu.Transliterator.createInstance(LATIN)
_junk = re.compile(r"[^0-9a-z ]+")
_space = re.compile(r"\s+")

NAME_KEYS = ("name", "name:en", "name:ru", "name:be", "alt_name", "old_name")


def normalize(s: str) -> str:
    """Lower-case ASCII words: the form names are indexed and queries are matched in."""
    return _space.sub(" ", _junk.sub(" ", _fold.transliterate(s))).strip()


def latin(s: str) -> str:
    """A readable Latin spelling of a name in any script, capitalization kept."""
    return _space.sub(" ", _latin.transliterate(s)).strip()


def display_name(tags: dict[str, str]) -> tuple[str, str | None]:
    """(what the rider reads, the original underneath when it differs): name:en, else a transliteration."""
    original = tags.get("name", "")
    shown = tags.get("name:en") or latin(original)
    return shown, (original if original and original != shown else None)


def search_names(tags: dict[str, str]) -> list[str]:
    """Every spelling the place is known by, the transliteration of its name included."""
    out: list[str] = []
    for key in NAME_KEYS:
        for value in (tags.get(key) or "").split(";"):
            if (value := value.strip()) and value not in out:
                out.append(value)
    if (name := tags.get("name")) and (t := latin(name)) not in out:
        out.append(t)
    return out
