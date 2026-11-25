"""The mechanism measured on four encoders, and the discipline that makes it count.

The effect replicating on four encoders was never in doubt; what this study adds
is the per-class quantity, which had been measured on one. These tests guard the
two ways that addition could quietly stop meaning anything: the registration
being written after the numbers, and the control encoder being allowed to drift
from the value it is supposed to reproduce.
"""

from __future__ import annotations

import inspect
import json

import pytest

from experiments import run_encoder_mechanism as mechanism
from experiments.config import RESULTS_DIR


class TestTheStudyIsWhatItClaims:
    def test_every_encoder_in_the_paper_is_covered(self):
        """Three encoders back the effect in the paper; the quantity has to face
        the same three, plus the one the main results use."""
        assert set(mechanism.ENCODERS) == {"MiniLM", "mpnet", "LaBSE", "bge-m3"}
        assert mechanism.CONTROL in mechanism.ENCODERS

    def test_the_alignment_step_cannot_see_an_accuracy(self):
        """Alignment is measured before the prediction is registered, so it must
        not reach any prediction, recall or argmax."""
        source = inspect.getsource(mechanism.alignment_rows)
        # The docstring says the words on purpose; what must not contain them is
        # the code, so it is scanned with the docstring removed.
        doc = mechanism.alignment_rows.__doc__ or ""
        code = source.replace(doc, "")
        for forbidden in ("argmax", "recall", "predict", "accuracy"):
            assert forbidden not in code, f"alignment_rows computes {forbidden}"

    def test_the_control_target_is_the_within_nace_figure(self):
        """The paper's headline +0.513 is pooled over two corpora. This study is
        NACE only, so reproducing the pooled number would be the wrong check."""
        published = json.loads((RESULTS_DIR / "predictor_search.json").read_text(encoding="utf-8"))
        assert mechanism.published_control() == pytest.approx(
            published["correlations"]["alignment_gain"]["within"]["NACE"])
        assert mechanism.published_control() != pytest.approx(
            published["correlations"]["alignment_gain"]["rho"])

    def test_captured_headroom_is_a_share_not_a_raw_gain(self):
        """A class already at 90% cannot gain much; the target has to divide by
        what was available or it mostly measures where a class started."""
        recall = {"terse": {"A": 0.5, "B": 0.9}, "rich": {"A": 0.75, "B": 0.95}}
        assert mechanism.captured(recall, "A") == pytest.approx(0.5)
        assert mechanism.captured(recall, "B") == pytest.approx(0.5)


class TestRegistrationDiscipline:
    PREREG = RESULTS_DIR / "encoder_mechanism_preregistration.json"
    RESULT = RESULTS_DIR / "encoder_mechanism.json"

    def test_results_do_not_exist_without_a_registration(self):
        if self.RESULT.exists():
            assert self.PREREG.exists(), (
                "encoder_mechanism.json exists without its preregistration: the study "
                "would be an exploration reported as a confirmation."
            )

    def test_the_registration_carries_no_per_class_accuracy(self):
        if not self.PREREG.exists():
            pytest.skip("not registered yet")
        payload = json.loads(self.PREREG.read_text(encoding="utf-8"))
        assert payload["method_fingerprint"] and payload["code_revision"]

        def keys(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield k.lower()
                    yield from keys(v)
            elif isinstance(node, list):
                for v in node:
                    yield from keys(v)

        for key in keys(payload):
            assert "recall" not in key and "rho" not in key, key
        assert "outcomes" not in payload

    def test_the_registration_says_what_was_already_known(self):
        """The corpus-level effect was public before this was registered. A
        registration that did not say so would overstate what it establishes."""
        if not self.PREREG.exists():
            pytest.skip("not registered yet")
        payload = json.loads(self.PREREG.read_text(encoding="utf-8"))
        assert "already_known_when_registered" in payload
        assert "per-class" in payload["already_known_when_registered"]

    def test_the_registration_matches_the_method_it_was_written_for(self):
        if not self.PREREG.exists():
            pytest.skip("not registered yet")
        payload = json.loads(self.PREREG.read_text(encoding="utf-8"))
        assert payload["method_fingerprint"] == mechanism.method_fingerprint(), (
            "the inputs or the measurement changed after registration; "
            "re-register, or restore what was registered"
        )

    def test_the_control_is_checked_before_the_other_encoders_are_believed(self):
        if not self.RESULT.exists():
            pytest.skip("not measured yet")
        result = json.loads(self.RESULT.read_text(encoding="utf-8"))
        control = next(o for o in result["outcomes"] if o["id"] == "control-reproduces")
        assert control["held"], (
            "the control encoder did not reproduce the published correlation, so the "
            "other three numbers in this file are withdrawn, not reported"
        )
