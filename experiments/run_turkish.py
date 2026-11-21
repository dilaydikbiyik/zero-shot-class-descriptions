#!/usr/bin/env python3
"""Turkish: the sixth and seventh corpora, with the outcome registered first.

    python -m experiments.run_turkish --preregister   # alignment, then the predictions
    python -m experiments.run_turkish                 # then, and only then, accuracy

Five corpora so far, two languages, both Indo-European. The question A8 asks is
whether the alignment account is about taxonomies or about German. Turkish is
agglutinative, so a class name shares far less surface form with the documents
it must attract than it does in German or English; if the account survives here
it is not living on shared morphology.

Two corpora, as a contrast rather than as two replications:

* MASSIVE (tr-TR): 60 intents inside 18 scenarios, named by identifiers
  (``alarm_set``). That is the NACE and Reuters regime, where a definition is
  predicted to pay. Its locales are human-localised parallel data, so the
  English split is a control on encoder quality that costs no translation.
* TTC-4900: 7 ordinary readable category names. That is the 20 Newsgroups and
  Brown regime, where a definition is predicted not to pay.

Four class-text arms, so language and authorship are not confounded: the
shipped English identifier, the terse Turkish name, a Turkish definition from
this project's assistant, and a Turkish definition written by a native speaker.
The fourth is empty until the author writes it and is skipped while it is.

The preregistration is written before any accuracy exists. Alignment is not
label-free — it is the cosine between a class vector and the centroid of that
class's own documents — but it uses no accuracy, which is the line this
project's registrations draw and the one `brown_preregistration.json` drew.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from datetime import datetime, timezone
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import f1_score

from experiments.config import DATA_DIR, RESULTS_DIR, SEED, ensure_dirs, set_seed
from experiments.effect_sizes import holm
from experiments.metrics import bootstrap_ci, mcnemar_exact
from experiments.run_rocchio import alignment, git_revision
from experiments.systems import get_embedder

CLASSES_JSON = DATA_DIR / "taxonomy" / "turkish_classes.json"
MASSIVE_CACHE = DATA_DIR / "cache" / "massive_tr.json"
MASSIVE_EN_CACHE = DATA_DIR / "cache" / "massive_en.json"
TTC_CACHE = DATA_DIR / "cache" / "ttc4900.json"

PREREGISTRATION = RESULTS_DIR / "turkish_preregistration.json"
RESULT = RESULTS_DIR / "turkish.json"

TRUNCATE = 1200          # characters, as in the Brown and Reuters studies
EVAL_SPLIT = "test"      # MASSIVE ships its own; TTC-4900 does not

ARMS = (
    "identifier",
    "terse_tr",
    "definition_assistant_tr",
    "definition_assistant_en",
    "definition_native_tr",
)
# The locales MASSIVE is measured in. Turkish is the subject; English is the
# control on encoder quality, used only for the language cross of P5.
LOCALES = ("tr", "en")
# The two steps the published studies take, in the same order Brown took them:
# first spell the opaque label out, then define it. Measuring them separately is
# what separates "the name was unreadable" from "the class needed explaining".
SPELL_OUT = ("identifier", "terse_tr")
DEFINE = ("terse_tr", "definition_assistant_tr")
DEFINE_NATIVE = ("terse_tr", "definition_native_tr")
WRITER = ("definition_assistant_tr", "definition_native_tr")
# The language cross: the same definition in two languages, on the same
# documents. Run once per document locale, which is the 2x2.
LANGUAGE = ("definition_assistant_en", "definition_assistant_tr")

CONTROL = "identifier"
TREATMENT = "definition_assistant_tr"


# ----------------------------------------------------------------- the corpora
def load_classes() -> Dict[str, Dict[str, Dict[str, str]]]:
    doc = json.loads(CLASSES_JSON.read_text(encoding="utf-8"))
    return {k: v for k, v in doc.items() if k != "metadata"}


def _require(path):
    if not path.exists():
        sys.exit(
            f"{path.name} is not cached. Fetch the corpora first:\n"
            "    python -m experiments.fetch_turkish"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_corpus(name: str, locale: str = "tr") -> Tuple[List[str], List[str]]:
    """Documents and gold labels for one evaluation setting, in one locale.

    MASSIVE's locales are parallel, so the English rows are the same content as
    the Turkish ones and carry the same gold labels; that is what makes them a
    control on the encoder rather than a second corpus. TTC-4900 has no
    parallel, and asking for one is a mistake rather than an empty result.
    """
    if name == "ttc4900":
        if locale != "tr":
            raise ValueError("TTC-4900 is Turkish only; it has no parallel locale")
        rows = _require(TTC_CACHE)
        return ([r["text"][:TRUNCATE] for r in rows], [r["category"] for r in rows])

    if locale not in LOCALES:
        raise ValueError(f"unknown locale {locale!r}")
    rows = _require(MASSIVE_CACHE if locale == "tr" else MASSIVE_EN_CACHE)
    rows = [r for r in rows if r["split"] == EVAL_SPLIT]
    field = "intent" if name == "massive_intent" else "scenario"
    return ([r["text"] for r in rows], [r[field] for r in rows])


def available_arms(entries: Dict[str, Dict[str, str]]) -> List[str]:
    """Arms with a text for every class. An arm half written is not an arm."""
    return [a for a in ARMS if all(entries[c].get(a) for c in entries)]


def class_texts(entries: Dict[str, Dict[str, str]], arm: str, names: Sequence[str]) -> List[str]:
    return [entries[n][arm] for n in names]


# ------------------------------------------------------------- the measurement
def embed(texts: Sequence[str]) -> np.ndarray:
    embedder = get_embedder()
    matrix = np.vstack(
        [np.asarray(embedder.embed_text(t), dtype=np.float64) for t in texts]
    )
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def predict(vectors: np.ndarray, docs: np.ndarray, names: Sequence[str]) -> List[str]:
    return [names[i] for i in (docs @ vectors.T).argmax(axis=1)]


def alignment_changes(
    docs: np.ndarray, gold: Sequence[str], entries: Dict, names: Sequence[str], arms: Sequence[str]
) -> Dict[str, Dict[str, float]]:
    """Per-class alignment for every arm. Uses labels, uses no accuracy."""
    return {
        arm: alignment(embed(class_texts(entries, arm, names)), docs, gold, names)
        for arm in arms
    }


def mean_change(per_class: Dict[str, Dict[str, float]], arm: str, frm: str = CONTROL) -> float:
    """Mean alignment change of one step, over the classes both arms cover."""
    if arm not in per_class or frm not in per_class:
        return 0.0
    base, treat = per_class[frm], per_class[arm]
    shared = [c for c in treat if c in base]
    return float(np.mean([treat[c] - base[c] for c in shared])) if shared else 0.0


def steps_for(arms: Sequence[str]) -> List[Tuple[str, str]]:
    """The steps measurable with the arms that are actually written."""
    candidates = [SPELL_OUT, DEFINE, DEFINE_NATIVE, WRITER]
    return [(a, b) for a, b in candidates if a in arms and b in arms]


def method_fingerprint() -> str:
    """Everything that fixes the documents, the class texts and the measurement."""
    parts = [
        f"SEED={SEED}",
        f"TRUNCATE={TRUNCATE}",
        f"EVAL_SPLIT={EVAL_SPLIT}",
        CLASSES_JSON.read_text(encoding="utf-8"),
    ]
    parts += [
        inspect.getsource(f)
        for f in (load_corpus, embed, predict, alignment_changes, mean_change)
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


# ------------------------------------------------------------ the registration
def predictions_from(changes: Dict[str, Dict]) -> List[Dict]:
    """The account's mechanical consequences for these corpora.

    Nothing here is a guess. Each direction is read off a measured alignment
    change, which is what makes it capable of being wrong.
    """
    out: List[Dict] = []
    for corpus, info in changes.items():
        for (frm, to), delta in info["step_change"].items():
            out.append(
                {
                    "id": f"direction::{corpus}::{frm}->{to}",
                    "corpus": corpus,
                    "step": [frm, to],
                    "claim": (
                        f"On {corpus}, moving from {frm} to {to} "
                        f"{'raises' if delta > 0 else 'does not raise'} Top-1 accuracy."
                    ),
                    "expected_sign": 1 if delta > 0 else -1,
                    "mean_alignment_change": delta,
                }
            )
        out.append(
            {
                "id": f"per-class::{corpus}",
                "corpus": corpus,
                "claim": (
                    f"On {corpus}, the per-class alignment change of the definition step "
                    "correlates positively with the share of available headroom captured."
                ),
            }
        )

    ordered = sorted(
        ((c, i["step_change"].get(DEFINE, 0.0)) for c, i in changes.items()),
        key=lambda kv: kv[1],
        reverse=True,
    )
    out.append(
        {
            "id": "ordering",
            "claim": (
                "The corpora's gains from the definition step follow the ordering of "
                "their mean alignment changes: " + " > ".join(c for c, _ in ordered) + "."
            ),
            "order": [c for c, _ in ordered],
        }
    )
    out.append(
        {
            "id": "language-match",
            "claim": (
                "On MASSIVE, a Turkish definition beats the same definition in English "
                "on Turkish documents, at the intent level and at the scenario level."
            ),
        }
    )
    out.append(
        {
            "id": "writer",
            "claim": (
                "The native speaker's definitions and the assistant's differ by less "
                "than the gap between either of them and the terse control."
            ),
            "note": "Registered because it is the one most likely to fail.",
        }
    )
    return out


def _measure_alignment(classes: Dict) -> Dict[str, Dict]:
    """Per-class alignment for every written arm, on every corpus. No accuracy."""
    changes: Dict[str, Dict] = {}
    for corpus, entries in classes.items():
        names = sorted(entries)
        arms = available_arms(entries)
        if TREATMENT not in arms:
            sys.exit(f"{corpus}: the '{TREATMENT}' arm is incomplete.")
        texts, gold = load_corpus(corpus)
        docs = embed(texts)
        per_class = alignment_changes(docs, gold, entries, names, arms)
        changes[corpus] = {
            "arms_measured": arms,
            "documents": len(texts),
            "classes": len(names),
            "alignment_per_class": per_class,
            "step_change": {
                step: mean_change(per_class, step[1], step[0]) for step in steps_for(arms)
            },
        }
    return changes


def _jsonable(changes: Dict) -> Dict:
    """Tuple keys are fine in Python and not in JSON."""
    out = json.loads(json.dumps({c: {k: v for k, v in i.items() if k != "step_change"}
                                 for c, i in changes.items()}))
    for corpus, info in changes.items():
        out[corpus]["step_change"] = {
            f"{a}->{b}": v for (a, b), v in info["step_change"].items()
        }
    return out


def preregister() -> int:
    set_seed()
    ensure_dirs()
    changes = _measure_alignment(load_classes())
    payload = {
        "study": "turkish",
        "registered_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "code_revision": git_revision(),
        "method_fingerprint": method_fingerprint(),
        "seed": SEED,
        "truncate": TRUNCATE,
        "eval_split": EVAL_SPLIT,
        "corpora": _jsonable(changes),
        "predictions": predictions_from(changes),
        "note": "Written before any accuracy on either Turkish corpus was computed.",
    }
    PREREGISTRATION.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"registered {len(payload['predictions'])} predictions -> {PREREGISTRATION}")
    for corpus, info in changes.items():
        for (frm, to), delta in info["step_change"].items():
            print(f"  {corpus}: {frm} -> {to}: alignment {delta:+.4f}")
    return 0


# ------------------------------------------------------------- the measurement
def score(docs: np.ndarray, gold: List[str], entries: Dict, arm: str,
          names: Sequence[str]) -> Dict:
    """Top-1 for one arm, with the per-document hits the McNemar tests need."""
    vectors = embed(class_texts(entries, arm, names))
    predicted = predict(vectors, docs, names)
    correct = [g == p for g, p in zip(gold, predicted)]
    lo, hi = bootstrap_ci(correct)
    return {
        "top1": float(np.mean(correct)),
        "ci": [lo, hi],
        "macro_f1": float(f1_score(gold, predicted, average="macro", zero_division=0)),
        "correct": correct,
    }


def headroom_correlation(per_class: Dict[str, Dict[str, float]], gold: List[str],
                         before: Dict, after: Dict, names: Sequence[str]) -> Dict:
    """Does a class that gained alignment capture more of the headroom it had?"""
    xs, ys = [], []
    for name in names:
        idx = [i for i, g in enumerate(gold) if g == name]
        if not idx or name not in per_class[DEFINE[0]] or name not in per_class[DEFINE[1]]:
            continue
        was = sum(before["correct"][i] for i in idx) / len(idx)
        now = sum(after["correct"][i] for i in idx) / len(idx)
        if was >= 1.0:          # no headroom left; the ratio is undefined
            continue
        xs.append(per_class[DEFINE[1]][name] - per_class[DEFINE[0]][name])
        ys.append((now - was) / (1.0 - was))
    if len(xs) < 3:
        return {"rho": None, "p_value": None, "n": len(xs)}
    rho, p = spearmanr(xs, ys)
    return {"rho": float(rho), "p_value": float(p), "n": len(xs)}


def measure() -> int:
    set_seed()
    ensure_dirs()
    if not PREREGISTRATION.exists():
        sys.exit(
            "No preregistration. Measuring first would make this an exploration:\n"
            "    make turkish-preregister"
        )
    registered = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    if registered["method_fingerprint"] != method_fingerprint():
        sys.exit(
            "The class texts or the measurement changed after registration.\n"
            "Restore what was registered, or register again and say so."
        )

    classes = load_classes()
    results: Dict[str, Dict] = {}
    family: Dict[str, float] = {}

    for corpus, entries in classes.items():
        names = sorted(entries)
        arms = available_arms(entries)
        texts, gold = load_corpus(corpus)
        docs = embed(texts)
        scored = {arm: score(docs, gold, entries, arm, names) for arm in arms}
        per_class = registered["corpora"][corpus]["alignment_per_class"]

        steps = {}
        for frm, to in steps_for(arms):
            test = mcnemar_exact(scored[to]["correct"], scored[frm]["correct"])
            key = f"{corpus}::{frm}->{to}"
            family[key] = test["p_value"]
            steps[f"{frm}->{to}"] = {
                "gain_pp": 100 * (scored[to]["top1"] - scored[frm]["top1"]),
                "mcnemar": test,
            }

        results[corpus] = {
            "documents": len(texts),
            "classes": len(names),
            "arms": {a: {k: v for k, v in s.items() if k != "correct"}
                     for a, s in scored.items()},
            "steps": steps,
            "headroom": headroom_correlation(
                per_class, gold, scored[DEFINE[0]], scored[DEFINE[1]], names
            ),
        }

        # The language cross, one row per document locale. MASSIVE only.
        if corpus.startswith("massive") and all(a in arms for a in LANGUAGE):
            cross = {}
            for locale in LOCALES:
                loc_texts, loc_gold = load_corpus(corpus, locale)
                loc_docs = embed(loc_texts)
                en = score(loc_docs, loc_gold, entries, LANGUAGE[0], names)
                tr = score(loc_docs, loc_gold, entries, LANGUAGE[1], names)
                test = mcnemar_exact(tr["correct"], en["correct"])
                key = f"{corpus}::language::{locale}"
                family[key] = test["p_value"]
                cross[locale] = {
                    "documents": len(loc_texts),
                    "english_definition_top1": en["top1"],
                    "turkish_definition_top1": tr["top1"],
                    "turkish_minus_english_pp": 100 * (tr["top1"] - en["top1"]),
                    "mcnemar": test,
                }
            results[corpus]["language_cross"] = cross

    adjusted = holm(family)
    payload = {
        "study": "turkish",
        "measured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "code_revision": git_revision(),
        "method_fingerprint": method_fingerprint(),
        "registered_at": registered["registered_at"],
        "corpora": results,
        "family": {
            "n_tests": len(family),
            "p_values": family,
            "holm_adjusted": adjusted,
            "surviving": sorted(k for k, v in adjusted.items() if v < 0.05),
        },
    }
    RESULT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    print(f"{RESULT}")
    for corpus, info in results.items():
        print(f"  {corpus}: {info['documents']} docs, {info['classes']} classes")
        for step, v in info["steps"].items():
            key = f"{corpus}::{step}"
            print(f"    {step}: {v['gain_pp']:+.1f} pp, "
                  f"p={family[key]:.2g}, Holm {adjusted[key]:.2g}")
    print(f"  family of {len(family)}, {len(payload['family']['surviving'])} surviving Holm")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--preregister",
        action="store_true",
        help="measure alignment, write the predictions, compute no accuracy",
    )
    args = parser.parse_args(argv)
    return preregister() if args.preregister else measure()


if __name__ == "__main__":
    raise SystemExit(main())
