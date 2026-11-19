"""The Turkish phase: the parts that must hold before any measurement is trusted.

These tests do not embed anything and do not need the corpora cached. They
guard the things that would quietly invalidate the study: a class text file
that has drifted out of step with the data, an arm that is half written being
treated as an arm, and a preregistration that was written after accuracy
existed.
"""

from __future__ import annotations

import json

import pytest

from experiments import fetch_turkish, run_turkish
from experiments.config import RESULTS_DIR

CLASSES = run_turkish.load_classes()
CORPORA = ("massive_intent", "massive_scenario", "ttc4900")


class TestClassTexts:
    def test_every_corpus_is_present(self):
        assert set(CLASSES) == set(CORPORA)

    def test_counts_match_the_published_taxonomies(self):
        assert len(CLASSES["massive_intent"]) == 60
        assert len(CLASSES["massive_scenario"]) == 18
        assert len(CLASSES["ttc4900"]) == 7

    def test_identifier_arm_is_the_key(self):
        """Arm 1 is the name as the dataset ships it, not a paraphrase of it."""
        for corpus in CORPORA:
            for key, entry in CLASSES[corpus].items():
                assert entry["identifier"] == key

    @pytest.mark.parametrize("arm", ["terse_tr", "definition_assistant_tr"])
    def test_written_arms_are_complete(self, arm):
        for corpus in CORPORA:
            missing = [k for k, v in CLASSES[corpus].items() if not v.get(arm)]
            assert not missing, f"{corpus}: {arm} missing for {missing}"

    def test_the_definition_is_longer_than_the_terse_name(self):
        """The treatment has to actually be a treatment."""
        for corpus in CORPORA:
            for key, entry in CLASSES[corpus].items():
                assert len(entry["definition_assistant_tr"]) > len(entry["terse_tr"]), key

    def test_ttc_keys_match_the_dataset_card(self):
        assert set(CLASSES["ttc4900"]) == set(fetch_turkish.TTC_CATEGORIES.values())


class TestArmSelection:
    def test_an_empty_arm_is_not_offered(self):
        entries = {"a": {"identifier": "a", "terse_tr": "a", "definition_assistant_tr": "d",
                         "definition_native_tr": ""}}
        assert "definition_native_tr" not in run_turkish.available_arms(entries)

    def test_a_half_written_arm_is_not_offered(self):
        """One class left blank must disqualify the whole arm, not be skipped."""
        entries = {
            "a": {"identifier": "a", "terse_tr": "a", "definition_assistant_tr": "d",
                  "definition_native_tr": "yazildi"},
            "b": {"identifier": "b", "terse_tr": "b", "definition_assistant_tr": "d",
                  "definition_native_tr": ""},
        }
        assert "definition_native_tr" not in run_turkish.available_arms(entries)

    def test_a_complete_arm_is_offered(self):
        entries = {
            "a": {"identifier": "a", "terse_tr": "a", "definition_assistant_tr": "d",
                  "definition_native_tr": "yazildi"},
        }
        assert "definition_native_tr" in run_turkish.available_arms(entries)


class TestMeanChange:
    def test_change_is_measured_against_the_identifier(self):
        per_class = {
            "identifier": {"a": 0.10, "b": 0.20},
            "definition_assistant_tr": {"a": 0.15, "b": 0.30},
        }
        assert run_turkish.mean_change(per_class, "definition_assistant_tr") == pytest.approx(0.075)

    def test_classes_without_documents_are_dropped_not_zeroed(self):
        """A class with no documents has no alignment; it must not enter the mean."""
        per_class = {
            "identifier": {"a": 0.10},
            "definition_assistant_tr": {"a": 0.20, "b": 0.90},
        }
        assert run_turkish.mean_change(per_class, "definition_assistant_tr") == pytest.approx(0.10)


class TestRegistrationDiscipline:
    """The study's whole claim to being confirmatory rests on this ordering."""

    PREREG = RESULTS_DIR / "turkish_preregistration.json"
    RESULT = RESULTS_DIR / "turkish.json"

    def test_results_do_not_exist_without_a_registration(self):
        if self.RESULT.exists():
            assert self.PREREG.exists(), (
                "turkish.json exists without turkish_preregistration.json: the study "
                "would be an exploration reported as a confirmation."
            )

    def test_registration_carries_a_fingerprint_and_no_accuracy(self):
        if not self.PREREG.exists():
            pytest.skip("not registered yet")
        payload = json.loads(self.PREREG.read_text(encoding="utf-8"))
        assert payload["method_fingerprint"]
        assert payload["code_revision"]
        assert payload["predictions"]
        flat = json.dumps(payload).lower()
        for forbidden in ("top1", "top_1", "accuracy", "macro_f1"):
            assert forbidden not in flat, f"{forbidden} appears in the registration"

    def test_registration_matches_the_class_texts_it_was_written_for(self):
        """If the class texts changed after registration, the fingerprint must not match."""
        if not self.PREREG.exists():
            pytest.skip("not registered yet")
        payload = json.loads(self.PREREG.read_text(encoding="utf-8"))
        assert payload["method_fingerprint"] == run_turkish.method_fingerprint(), (
            "the class texts or the measurement changed after registration; "
            "re-register, or restore what was registered"
        )
