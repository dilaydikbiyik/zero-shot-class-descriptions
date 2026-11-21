"""The externally authored control: what must hold for it to count as external.

The point of this arm is that nobody on this project chose its words. These
tests guard the two ways that could quietly stop being true: the text drifting
away from the official source's own structure, and a missing note being filled
in with something of ours.
"""

from __future__ import annotations

import json

import pytest

from experiments import fetch_official_nace as official
from experiments.config import DATA_DIR

PATH = DATA_DIR / "taxonomy" / "sectors_official.json"
pytestmark = pytest.mark.skipif(not PATH.exists(), reason="official notes not fetched")


@pytest.fixture(scope="module")
def document():
    return json.loads(PATH.read_text(encoding="utf-8"))


class TestCoverage:
    def test_the_sections_are_this_project_s_sections(self, document):
        ours = set(json.loads((DATA_DIR / "taxonomy" / "sectors.json")
                              .read_text(encoding="utf-8"))["sectors"])
        assert set(document["sections"]) == ours

    def test_missing_notes_are_recorded_not_filled(self, document):
        """T and U have no official note. Substituting the title would make this
        arm partly a terse arm, and the comparison would no longer be about
        authorship."""
        missing = document["metadata"]["sections_without_a_note"]
        for code in missing:
            section = document["sections"][code]
            assert section["official_full"] == ""
            assert section["official_first_sentence"] == ""
            assert section["title"], "the title is still recorded, just not used as a note"

    def test_attribution_is_carried(self, document):
        assert "Statistisches Bundesamt" in document["metadata"]["attribution"]
        assert document["metadata"]["source"].startswith("https://")


class TestTheTwoArms:
    def test_the_first_sentence_is_a_prefix_of_the_full_note(self, document):
        for code, section in document["sections"].items():
            if section["official_full"]:
                assert section["official_full"].startswith(
                    section["official_first_sentence"]
                ), code

    def test_the_first_sentence_is_shorter_where_the_note_is_long(self, document):
        long_notes = [s for s in document["sections"].values() if s["note_words"] > 40]
        assert long_notes, "expected at least one long official note"
        for section in long_notes:
            assert len(section["official_first_sentence"].split()) < section["note_words"]


class TestSentenceSplitting:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Dieser Abschnitt umfasst d. h. Dinge. Und mehr.",
             "Dieser Abschnitt umfasst d. h. Dinge."),
            ("Ein Satz z. B. mit Abkürzung. Zweiter Satz.",
             "Ein Satz z. B. mit Abkürzung."),
            ("Nur ein Satz ohne Ende", "Nur ein Satz ohne Ende"),
        ],
    )
    def test_abbreviations_do_not_end_a_sentence(self, text, expected):
        assert official.first_sentence(text) == expected
