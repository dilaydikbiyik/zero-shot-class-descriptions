#!/usr/bin/env python3
"""Does the description effect survive class texts nobody here wrote?

    python -m experiments.run_official_nace --preregister   # commit the prediction
    python -m experiments.run_official_nace                 # then test it

`run_description_source.py` already separates the effect from one particular
writer: an independent 7B model, given the terse control and nothing else,
reproduces part of it. What it cannot separate is the project itself. Every arm
of that comparison was written for this study, by a writer who had been shown
this taxonomy and, in the assistant's case, these documents. The objection that
survives is the plainest one a reviewer can make: the descriptions were written
by the people who then measured them.

The control that answers it is not another writer of ours. It is the text a
German registrar actually classifies against: the explanatory notes of WZ 2008,
the German implementation of NACE Rev. 2, published by the Statistisches
Bundesamt in 2008, years before this project and with no knowledge of it.
`fetch_official_nace.py` puts them in `data/taxonomy/sectors_official.json`.

Four class texts, one encoder, the same documents:

  1. the terse German control — the section's short name, hand-translated,
     which is condition 2 of the description study and the control of the
     description-source study, so the three studies share a baseline;
  2. the assistant's definitions — the paper's own;
  3. the official note, verbatim;
  4. the official note's first sentence.

Why the official text enters twice
----------------------------------
Because a single official arm would confound authorship with length. Over the
nineteen sections that carry a note, the note runs to a median of 78 words and
670 for section C, where this project's own descriptions are 6 to 25 words with
a median of 14. A gain from arm 3 alone could be read either as "someone
outside the project wrote it" or as "there was simply more text". Arm 4 cuts
each note to its first sentence: a median of 19 words, which sits inside this
project's own band.

The match is close at the median and imperfect in the tail — six sections have
a first sentence longer than this project's longest description, the worst
being L at 48 words. So arm 4 narrows the length gap from nearly sixfold to within seven words of
the assistant's own arm rather than closing it, and the registration records the mean words per class for
every arm so that a length reading stays checkable afterwards. What the two
arms buy is the comparison between them: a length explanation has to predict
that arms differing nearly sixfold in length behave differently, and an authorship
explanation has to predict that they behave alike.

The label space
---------------
Sections T and U carry no official note, so no official arm can supply a class
text for them, and filling them from their title would make the official arms
partly terse arms. They are dropped from the label space **in all four arms**,
including the two that could have covered them, because an argmax over 19
classes is an easier problem than one over 21 and the arms have to face the
same problem. No evaluation document is lost: the 299 labelled documents cover
18 sections and neither T nor U is among them. The consequence is that the
accuracies here are 19-way and not comparable to the paper's 21-way figures;
the control is re-run inside this study so that every number it reports is
compared against a baseline measured on the same label space.

The prediction is registered before any accuracy is computed, and it is not
authored: the alignment account says a class text buys alignment with the
documents it has to attract, so the measured alignment changes fix the expected
ordering of the gains. If the official notes raise alignment and do not raise
accuracy, the account is wrong here, and that is recorded as a failure.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from datetime import datetime, timezone
from typing import Dict, List, Sequence

import numpy as np
from scipy.stats import spearmanr

from experiments.config import RESULTS_DIR, ROOT, SEED, ensure_dirs, set_seed
from experiments.data import load_labeled_samples
from experiments.metrics import bootstrap_ci, mcnemar_exact
from experiments.run_description_study import LITERAL_GERMAN
from experiments.run_rocchio import alignment, encode, git_revision, unit_rows

PREREGISTRATION = RESULTS_DIR / "official_nace_preregistration.json"
RESULT = RESULTS_DIR / "official_nace.json"
TAXONOMY = ROOT / "data" / "taxonomy"
OFFICIAL = TAXONOMY / "sectors_official.json"

CONTROL = "terse German name"
ASSISTANT = "definitions by the assistant"
OFFICIAL_FULL = "the official note, verbatim"
OFFICIAL_SENTENCE = "the official note, first sentence"
ARMS = (CONTROL, ASSISTANT, OFFICIAL_FULL, OFFICIAL_SENTENCE)
EXTERNAL = (OFFICIAL_FULL, OFFICIAL_SENTENCE)


def _load(name: str) -> Dict:
    return json.loads((TAXONOMY / name).read_text(encoding="utf-8"))


def codes() -> List[str]:
    """The sections every arm can name: those with an official note.

    Restricting the space is the honest move and the restriction has to apply
    to all four arms. A class the external arms cannot describe is a class they
    would never predict, which would hand them a smaller haystack than the
    arms that can describe it.
    """
    official = _load("sectors_official.json")["sections"]
    terse = _load("sectors_v1.json")["sectors"]
    return sorted(c for c in terse if official.get(c, {}).get("official_full"))


def class_texts() -> Dict[str, Dict[str, str]]:
    """The four conditions, each a class text per section.

    Every arm carries the control's section name, so the only part that varies
    between arms is the description that follows it. That is the same
    construction `run_description_source.py` uses, and keeping it means the
    three studies differ in their descriptions and in nothing else.
    """
    old = _load("sectors_v1.json")["sectors"]
    new = _load("sectors.json")["sectors"]
    official = _load("sectors_official.json")["sections"]
    cs = codes()

    def with_name(c: str, body: str) -> str:
        return f"{old[c].get('name', '')}. {body}".strip()

    return {
        CONTROL: {c: with_name(c, LITERAL_GERMAN.get(c, old[c].get("description", ""))) for c in cs},
        ASSISTANT: {c: with_name(c, new[c].get("description", "")) for c in cs},
        OFFICIAL_FULL: {c: with_name(c, official[c]["official_full"]) for c in cs},
        OFFICIAL_SENTENCE: {c: with_name(c, official[c]["official_first_sentence"]) for c in cs},
    }


def vectors(texts: Dict[str, str], cs: Sequence[str]) -> np.ndarray:
    return unit_rows(np.vstack([encode([texts[c]]) for c in cs]))


def predictions_from(changes: Dict[str, float]) -> List[Dict]:
    """What the alignment account implies, derived mechanically from the changes.

    Nothing here is a hunch. Each direction is read off a measured alignment
    change, so there is no step at which a prediction could be chosen to match
    an accuracy that has not been computed yet.
    """
    ranked = sorted(changes, key=changes.get, reverse=True)
    out = [{"id": f"direction-{name}",
            "claim": f"Against the control, {name} {'raises' if d > 0 else 'lowers'} Top-1 accuracy.",
            "condition": name, "expected_sign": 1 if d > 0 else -1}
           for name, d in changes.items()]
    out.append({"id": "ordering",
                "claim": "The gains follow the order of the alignment changes: " + " > ".join(ranked) + ".",
                "order": ranked})
    agree = np.sign(changes[OFFICIAL_FULL]) == np.sign(changes[OFFICIAL_SENTENCE])
    out.append({"id": "authorship-not-length",
                "claim": ("The two official arms move accuracy in the same direction as each other"
                          if agree else
                          "The two official arms move accuracy in opposite directions, as their "
                          "alignment changes do"),
                "expected_agreement": bool(agree),
                "why": ("They differ by nearly a factor of six in length and not at all in authorship, so a length "
                        "reading of the effect predicts they diverge and an authorship reading "
                        "predicts they agree. Which of the two is predicted here is fixed by the "
                        "measured alignment changes, not chosen.")})
    out.append({"id": "per-class",
                "claim": "For the official note, the per-class alignment change correlates "
                         "positively with the share of available headroom captured "
                         "(Spearman rho > 0)."})
    return out


def method_fingerprint() -> str:
    """A hash of the class texts and of everything that turns them into a number."""
    parts = [f"SEED={SEED}"]
    parts += [inspect.getsource(f) for f in (codes, class_texts, vectors, alignment, encode, unit_rows)]
    for name in ("sectors_v1.json", "sectors.json", "sectors_official.json"):
        parts.append(hashlib.sha256((TAXONOMY / name).read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def measured(samples) -> Dict:
    """Alignment per class for each arm, which needs no accuracy."""
    cs = codes()
    docs = unit_rows(np.vstack([encode([s.purpose]) for s in samples]))
    gold = [s.true_sector for s in samples]
    texts = class_texts()
    per_class = {name: alignment(vectors(t, cs), docs, gold, cs) for name, t in texts.items()}
    return {"codes": cs, "docs": docs, "gold": gold, "texts": texts, "alignment": per_class}


def mean_words(texts: Dict[str, str]) -> float:
    return float(np.mean([len(t.split()) for t in texts.values()]))


def preregister() -> int:
    if PREREGISTRATION.exists():
        print(f"{PREREGISTRATION} already exists; a prediction is made once.", file=sys.stderr)
        return 1
    samples = load_labeled_samples()
    state = measured(samples)
    base = state["alignment"][CONTROL]
    per_class = {name: {c: state["alignment"][name][c] - base[c] for c in base}
                 for name in ARMS if name != CONTROL}
    changes = {name: float(np.mean(list(v.values()))) for name, v in per_class.items()}
    official_meta = _load("sectors_official.json")["metadata"]
    for name, change in changes.items():
        print(f"  {name:36s} mean alignment change {change:+.4f}")
    payload = {
        "study": "official_nace",
        "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_revision": git_revision(),
        "method_fingerprint": method_fingerprint(),
        "seed": SEED,
        "external_source": {
            "classification": official_meta["classification"],
            "attribution": official_meta["attribution"],
            "url": official_meta["source"],
            "written_before_this_project": True,
        },
        "label_space": {
            "codes": state["codes"],
            "n_classes": len(state["codes"]),
            "dropped": official_meta["sections_without_a_note"],
            "why_dropped": "No official explanatory note exists for these sections, so no "
                           "external arm can describe them; dropping them from every arm keeps "
                           "the argmax over the same classes in all four conditions.",
            "documents_lost": 0,
            "comparable_to_the_paper": False,
        },
        "n_documents": len(samples),
        "classes_measured": len(base),
        "mean_words_per_class": {name: mean_words(t) for name, t in state["texts"].items()},
        "mean_alignment_change": changes,
        "alignment_change_per_class": per_class,
        "predictions": predictions_from(changes),
        "note": "Written before any accuracy under the official class texts was computed.",
    }
    PREREGISTRATION.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    for p in payload["predictions"]:
        print(f"  PREDICTION {p['id']}: {p['claim']}")
    print(f"Wrote {PREREGISTRATION}. Commit it before running the accuracy step.")
    return 0


def evaluate() -> int:
    if not PREREGISTRATION.exists():
        print("No preregistration: run with --preregister and commit the file first.", file=sys.stderr)
        return 1
    registered = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    if registered.get("method_fingerprint") != method_fingerprint():
        print("The class texts or the method changed after the prediction was registered; "
              "refusing to test it.", file=sys.stderr)
        return 1

    samples = load_labeled_samples()
    state = measured(samples)
    cs, docs, gold = state["codes"], state["docs"], state["gold"]
    present = [c for c in cs if c in set(gold)]

    hits, report = {}, {}
    for name, texts in state["texts"].items():
        order = np.argsort(-(docs @ vectors(texts, cs).T), axis=1)
        predicted = [cs[order[i, 0]] for i in range(len(gold))]
        hits[name] = [g == p for g, p in zip(gold, predicted)]
        lo, hi = bootstrap_ci(hits[name])
        report[name] = {
            "top1_accuracy": float(np.mean(hits[name])),
            "top1_ci95": [lo, hi],
            "top3_accuracy": float(np.mean([gold[i] in [cs[j] for j in order[i, :3]]
                                            for i in range(len(gold))])),
            "mean_words_per_class": mean_words(texts),
        }

    recall = {name: {c: float(np.mean([h for h, g in zip(hits[name], gold) if g == c]))
                     for c in present} for name in hits}
    for name in ARMS:
        if name == CONTROL:
            continue
        report[name]["gain_pp"] = 100 * float(np.mean(hits[name]) - np.mean(hits[CONTROL]))
        report[name]["mcnemar_vs_control"] = mcnemar_exact(hits[CONTROL], hits[name])
    for name in EXTERNAL:
        report[name]["mcnemar_vs_assistant"] = mcnemar_exact(hits[ASSISTANT], hits[name])
    report[OFFICIAL_SENTENCE]["mcnemar_vs_official_full"] = mcnemar_exact(
        hits[OFFICIAL_FULL], hits[OFFICIAL_SENTENCE])

    pooled = [(registered["alignment_change_per_class"][OFFICIAL_FULL][c],
               (recall[OFFICIAL_FULL][c] - recall[CONTROL][c]) / (1 - recall[CONTROL][c]))
              for c in present if recall[CONTROL][c] < 0.999]
    rho, p_rho = spearmanr([a for a, _ in pooled], [s for _, s in pooled])

    outcomes = []
    for pred in registered["predictions"]:
        if pred["id"].startswith("direction-"):
            held = np.sign(report[pred["condition"]]["gain_pp"]) == pred["expected_sign"]
        elif pred["id"] == "ordering":
            gains = [report[c]["gain_pp"] for c in pred["order"]]
            held = all(a > b for a, b in zip(gains, gains[1:]))
        elif pred["id"] == "authorship-not-length":
            agree = np.sign(report[OFFICIAL_FULL]["gain_pp"]) == np.sign(
                report[OFFICIAL_SENTENCE]["gain_pp"])
            held = bool(agree) == pred["expected_agreement"]
        else:
            held = bool(rho > 0)
        outcomes.append({**pred, "held": bool(held)})
        print(f"  {'HELD  ' if held else 'FAILED'} {pred['claim']}")

    payload = {
        "study": "official_nace",
        "preregistration": PREREGISTRATION.name,
        "registered_at": registered["registered_at"],
        "external_source": registered["external_source"],
        "label_space": registered["label_space"],
        "n": len(samples),
        "conditions": report,
        "mean_alignment_change": registered["mean_alignment_change"],
        "per_class": {"n": len(pooled), "rho": float(rho), "p": float(p_rho)},
        "outcomes": outcomes,
    }
    RESULT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name in ARMS:
        r = report[name]
        gain = f"{r['gain_pp']:+.1f} pp" if "gain_pp" in r else "control"
        print(f"  {name:36s} Top-1 {r['top1_accuracy']:.1%}  {gain}"
              f"  ({r['mean_words_per_class']:.0f} words/class)")
    print(f"  per-class rho = {rho:+.3f} (p = {p_rho:.4f}, n = {len(pooled)})")
    print(f"Wrote {RESULT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregister", action="store_true")
    args = parser.parse_args()
    if not OFFICIAL.exists():
        print("Fetch the official notes first: python -m experiments.fetch_official_nace",
              file=sys.stderr)
        return 1
    set_seed()
    ensure_dirs()
    return preregister() if args.preregister else evaluate()


if __name__ == "__main__":
    sys.exit(main())
