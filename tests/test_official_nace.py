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
from experiments import run_official_nace as study
from experiments.config import DATA_DIR, RESULTS_DIR
from experiments.data import load_labeled_samples

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


class TestTheStudy:
    """The arms have to face the same problem, or the comparison is not one."""

    def test_the_label_space_is_the_sections_with_a_note(self, document):
        missing = set(document["metadata"]["sections_without_a_note"])
        assert set(study.codes()).isdisjoint(missing)
        assert set(study.codes()) == set(document["sections"]) - missing

    def test_every_arm_covers_exactly_that_space(self):
        """A class one arm cannot name is a class it would never predict, which
        would hand it a smaller haystack than the arms that can name it."""
        texts = study.class_texts()
        assert set(texts) == set(study.ARMS)
        for arm, per_class in texts.items():
            assert set(per_class) == set(study.codes()), arm
            assert all(t.strip() for t in per_class.values()), arm

    def test_dropping_the_two_sections_loses_no_document(self, document):
        """If it cost documents, the restriction would change the corpus and not
        only the label space."""
        missing = set(document["metadata"]["sections_without_a_note"])
        gold = {s.true_sector for s in load_labeled_samples()}
        assert gold.isdisjoint(missing)
        assert gold <= set(study.codes())

    def test_the_arms_differ_only_in_the_description(self):
        """Each arm carries the control's section name, so what varies between
        arms is the text after it and nothing else."""
        texts = study.class_texts()
        for code in study.codes():
            prefix = texts[study.CONTROL][code].split(".")[0]
            for arm in study.ARMS:
                assert texts[arm][code].startswith(prefix), (arm, code)

    def test_the_two_official_arms_separate_length_from_authorship(self):
        """The whole reason the official text enters twice: same author, lengths
        far enough apart that a length reading has to predict they diverge."""
        texts = study.class_texts()
        full = study.mean_words(texts[study.OFFICIAL_FULL])
        sentence = study.mean_words(texts[study.OFFICIAL_SENTENCE])
        assistant = study.mean_words(texts[study.ASSISTANT])
        assert full > 3 * sentence
        assert abs(sentence - assistant) < 0.5 * assistant


class TestPredictionsAreDerivedNotAuthored:
    def test_each_direction_follows_its_alignment_change(self):
        changes = {study.ASSISTANT: 0.08, study.OFFICIAL_FULL: 0.02,
                   study.OFFICIAL_SENTENCE: -0.01}
        by_id = {p["id"]: p for p in study.predictions_from(changes)}
        for arm, change in changes.items():
            assert by_id[f"direction-{arm}"]["expected_sign"] == (1 if change > 0 else -1)
        assert by_id["ordering"]["order"] == [study.ASSISTANT, study.OFFICIAL_FULL,
                                              study.OFFICIAL_SENTENCE]

    def test_the_length_prediction_is_fixed_by_the_measurement(self):
        """Whether the two official arms are predicted to agree is read off the
        alignment, not chosen to suit the conclusion the control was built for."""
        agreeing = study.predictions_from({study.ASSISTANT: 0.08, study.OFFICIAL_FULL: 0.02,
                                           study.OFFICIAL_SENTENCE: 0.01})
        diverging = study.predictions_from({study.ASSISTANT: 0.08, study.OFFICIAL_FULL: 0.02,
                                            study.OFFICIAL_SENTENCE: -0.01})
        assert {p["id"]: p for p in agreeing}["authorship-not-length"]["expected_agreement"]
        assert not {p["id"]: p for p in diverging}["authorship-not-length"]["expected_agreement"]


class TestRegistrationDiscipline:
    PREREG = RESULTS_DIR / "official_nace_preregistration.json"
    RESULT = RESULTS_DIR / "official_nace.json"

    def test_results_do_not_exist_without_a_registration(self):
        if self.RESULT.exists():
            assert self.PREREG.exists(), (
                "official_nace.json exists without its preregistration: the study "
                "would be an exploration reported as a confirmation."
            )

    def test_registration_carries_a_fingerprint_and_no_measured_accuracy(self):
        if not self.PREREG.exists():
            pytest.skip("not registered yet")
        payload = json.loads(self.PREREG.read_text(encoding="utf-8"))
        assert payload["method_fingerprint"]
        assert payload["code_revision"]
        assert payload["predictions"]

        def keys(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield k.lower()
                    yield from keys(v)
            elif isinstance(node, list):
                for v in node:
                    yield from keys(v)

        for key in keys(payload):
            assert "accuracy" not in key and "top1" not in key and "gain" not in key, key
        assert "outcomes" not in payload

    def test_registration_records_the_restricted_label_space(self):
        """A reader must not be able to mistake a 19-way accuracy for the
        paper's 21-way one."""
        if not self.PREREG.exists():
            pytest.skip("not registered yet")
        space = json.loads(self.PREREG.read_text(encoding="utf-8"))["label_space"]
        assert space["n_classes"] == len(study.codes())
        assert space["documents_lost"] == 0
        assert space["comparable_to_the_paper"] is False

    def test_registration_matches_the_class_texts_it_was_written_for(self):
        if not self.PREREG.exists():
            pytest.skip("not registered yet")
        payload = json.loads(self.PREREG.read_text(encoding="utf-8"))
        assert payload["method_fingerprint"] == study.method_fingerprint(), (
            "the class texts or the measurement changed after registration; "
            "re-register, or restore what was registered"
        )
