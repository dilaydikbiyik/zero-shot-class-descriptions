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

from experiments.config import DATA_DIR, RESULTS_DIR, SEED, ensure_dirs, set_seed
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

ARMS = ("identifier", "terse_tr", "definition_assistant_tr", "definition_native_tr")
# The step whose gain the predictions are about, per corpus family.
TREATMENT = "definition_assistant_tr"
CONTROL = "identifier"


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


def load_corpus(name: str) -> Tuple[List[str], List[str]]:
    """Documents and gold labels for one of the three evaluation settings."""
    if name == "ttc4900":
        rows = _require(TTC_CACHE)
        return ([r["text"][:TRUNCATE] for r in rows], [r["category"] for r in rows])

    rows = _require(MASSIVE_CACHE)
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


def mean_change(per_class: Dict[str, Dict[str, float]], arm: str) -> float:
    base, treat = per_class[CONTROL], per_class[arm]
    shared = [c for c in treat if c in base]
    return float(np.mean([treat[c] - base[c] for c in shared])) if shared else 0.0


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
def predictions_from(changes: Dict[str, Dict[str, float]]) -> List[Dict]:
    """The account's mechanical consequences for these corpora.

    Nothing here is a guess. Each claim is read off a measured alignment change,
    which is why it can be wrong and why it is worth registering.
    """
    out: List[Dict] = []
    for corpus, per_arm in changes.items():
        delta = per_arm["mean_change"][TREATMENT]
        out.append(
            {
                "id": f"direction-{corpus}",
                "corpus": corpus,
                "claim": (
                    f"On {corpus}, replacing the identifier with a Turkish definition "
                    f"{'raises' if delta > 0 else 'does not raise'} Top-1 accuracy."
                ),
                "expected_sign": 1 if delta > 0 else -1,
                "mean_alignment_change": delta,
            }
        )
        out.append(
            {
                "id": f"per-class-{corpus}",
                "corpus": corpus,
                "claim": (
                    f"On {corpus}, the per-class alignment change correlates positively "
                    "with the share of available headroom captured (rho > 0)."
                ),
            }
        )

    ordered = sorted(
        ((c, v["mean_change"][TREATMENT]) for c, v in changes.items()),
        key=lambda kv: kv[1],
        reverse=True,
    )
    out.append(
        {
            "id": "ordering",
            "claim": (
                "The corpora's gains follow the ordering of their mean alignment "
                "changes: " + " > ".join(c for c, _ in ordered) + "."
            ),
            "order": [c for c, _ in ordered],
        }
    )
    out.append(
        {
            "id": "language-match",
            "claim": (
                "On MASSIVE, Turkish class texts beat English ones on Turkish documents, "
                "at the intent level and at the scenario level."
            ),
        }
    )
    out.append(
        {
            "id": "writer",
            "claim": (
                "The native speaker's definitions and the assistant's differ by less than "
                "the gap between either of them and the terse control."
            ),
            "note": "Registered because it is the one most likely to fail.",
        }
    )
    return out


def preregister() -> int:
    set_seed()
    ensure_dirs()
    classes = load_classes()

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
            "mean_change": {a: mean_change(per_class, a) for a in arms},
        }

    payload = {
        "study": "turkish",
        "registered_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "code_revision": git_revision(),
        "method_fingerprint": method_fingerprint(),
        "seed": SEED,
        "truncate": TRUNCATE,
        "eval_split": EVAL_SPLIT,
        "corpora": changes,
        "predictions": predictions_from(changes),
        "note": "Written before any accuracy on either Turkish corpus was computed.",
    }
    PREREGISTRATION.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"registered {len(payload['predictions'])} predictions -> {PREREGISTRATION}")
    for corpus, v in changes.items():
        print(
            f"  {corpus}: {v['documents']} docs, {v['classes']} classes, "
            f"mean alignment change {v['mean_change'][TREATMENT]:+.4f}"
        )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--preregister",
        action="store_true",
        help="measure alignment, write the predictions, compute no accuracy",
    )
    args = parser.parse_args(argv)
    if args.preregister:
        return preregister()
    sys.exit(
        "The measurement step is not written yet. Register first:\n"
        "    python -m experiments.run_turkish --preregister"
    )


if __name__ == "__main__":
    raise SystemExit(main())
