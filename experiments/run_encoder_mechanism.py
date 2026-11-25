#!/usr/bin/env python3
"""Is the quantity encoder-independent, or only the effect?

    python -m experiments.run_encoder_mechanism --preregister   # commit the prediction
    python -m experiments.run_encoder_mechanism                 # then test it

The description effect replicates on four encoders: +26.8 points on the
118M-parameter MiniLM of the main results, and +13.7, +16.1 and +17.7 on mpnet,
LaBSE and bge-m3. That is the *effect* reproducing. The claim this project
actually makes is about a *quantity* — that what a class text buys is alignment
with the documents it must attract, and that the per-class change in alignment
predicts which classes gain. Until now that per-class relation had been measured
on one encoder only (`run_predictor_search.py`), so a reviewer could accept the
effect and still say the mechanism rests on a single model.

This module measures the same relation, with the same definitions, on all four.
Nothing about the method changes between encoders: the documents, the two class
texts and the formula are fixed, and only the model that embeds them varies.

What was already known, and what was not
----------------------------------------
The corpus-level accuracy of every encoder here was computed before this study
was registered — it is in `results/description_study_*.json` and in the paper.
What did not exist for mpnet, LaBSE or bge-m3 is any per-class quantity: not the
per-class recall, not the alignment, not their correlation. Those are what the
prediction is about, and they are computed only after it is committed.

MiniLM is included although its correlation is published, and it is the control
on the method rather than a result: this module re-derives it from scratch, and
if it does not reproduce the published value the implementation is wrong and the
other three numbers mean nothing.
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

from experiments import systems
from experiments.config import EMBEDDING_MODEL, RESULTS_DIR, ROOT, SEED, ensure_dirs, set_seed
from experiments.run_predictor_search import load_nace
from experiments.run_rocchio import git_revision, unit_rows
from experiments.systems import LABSE_MODEL, MPNET_MODEL

PREREGISTRATION = RESULTS_DIR / "encoder_mechanism_preregistration.json"
RESULT = RESULTS_DIR / "encoder_mechanism.json"
PUBLISHED = RESULTS_DIR / "predictor_search.json"

BGE_MODEL = "BAAI/bge-m3"
ENCODERS = {
    "MiniLM": EMBEDDING_MODEL,
    "mpnet": MPNET_MODEL,
    "LaBSE": LABSE_MODEL,
    "bge-m3": BGE_MODEL,
}
CONTROL = "MiniLM"
# The control target is the *within-NACE* correlation of `predictor_search`
# (+0.556), not the paper's headline +0.513, which is pooled over NACE and 20
# Newsgroups. This module measures NACE only, so the within-NACE figure is the
# one it has to reproduce before any other number it prints can be believed.
TOLERANCE = 0.01


def embed(texts: Sequence[str], model_name: str) -> np.ndarray:
    """One text at a time, as every other study in this project embeds them."""
    embedder = systems.get_embedder(model_name)
    return unit_rows(np.vstack([np.asarray(embedder.embed_text(t), dtype=np.float64)
                                for t in texts]))


def centroids_of(docs: np.ndarray, gold: Sequence[str], names: Sequence[str]) -> Dict[str, np.ndarray]:
    out = {}
    for c in names:
        idx = [i for i, g in enumerate(gold) if g == c]
        m = docs[idx].mean(axis=0)
        out[c] = m / np.linalg.norm(m)
    return out


def alignment_rows(model_name: str) -> List[Dict]:
    """Per-class alignment under both class texts. No accuracy is computed here.

    Alignment uses the gold labels, to know which documents belong to a class.
    What it does not use is any prediction, so nothing in this function can see
    whether a class is classified correctly.
    """
    names, documents, terse, rich = load_nace()
    flat = [d for c in names for d in documents[c]]
    gold = [c for c in names for _ in documents[c]]
    docs = embed(flat, model_name)
    terse_vectors = embed([terse[c] for c in names], model_name)
    rich_vectors = embed([rich[c] for c in names], model_name)
    centroids = centroids_of(docs, gold, names)
    return [{
        "class": c,
        "alignment_terse": float(terse_vectors[i] @ centroids[c]),
        "alignment_gain": float(rich_vectors[i] @ centroids[c] - terse_vectors[i] @ centroids[c]),
    } for i, c in enumerate(names)]


def recall_rows(model_name: str) -> Dict[str, Dict[str, float]]:
    """Per-class recall under both class texts. This is the step that uses accuracy."""
    names, documents, terse, rich = load_nace()
    flat = [d for c in names for d in documents[c]]
    gold = [c for c in names for _ in documents[c]]
    docs = embed(flat, model_name)
    out = {}
    for label, texts in (("terse", terse), ("rich", rich)):
        vectors = embed([texts[c] for c in names], model_name)
        predicted = [names[i] for i in np.argmax(docs @ vectors.T, axis=1)]
        out[label] = {c: float(np.mean([predicted[i] == c for i in range(len(gold)) if gold[i] == c]))
                      for c in names}
    return out


def captured(recall: Dict[str, Dict[str, float]], c: str) -> float:
    """The share of the headroom a class had that it actually took."""
    return (recall["rich"][c] - recall["terse"][c]) / (1 - recall["terse"][c])


def correlate(rows: Sequence[Dict], recall: Dict[str, Dict[str, float]]) -> Dict:
    usable = [r for r in rows if recall["terse"][r["class"]] < 0.999]
    rho, p = spearmanr([r["alignment_gain"] for r in usable],
                       [captured(recall, r["class"]) for r in usable])
    return {"n_classes": len(usable), "rho": float(rho), "p": float(p)}


def method_fingerprint() -> str:
    parts = [f"SEED={SEED}", repr(sorted(ENCODERS.items()))]
    parts += [inspect.getsource(f) for f in
              (embed, centroids_of, alignment_rows, recall_rows, captured, correlate, load_nace)]
    for name in ("sectors_v1.json", "sectors.json"):
        parts.append(hashlib.sha256((ROOT / "data" / "taxonomy" / name).read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def published_control() -> float:
    """The correlation the control encoder has to reproduce."""
    return float(json.loads(PUBLISHED.read_text(encoding="utf-8"))
                 ["correlations"]["alignment_gain"]["within"]["NACE"])


def preregister() -> int:
    if PREREGISTRATION.exists():
        print(f"{PREREGISTRATION} already exists; a prediction is made once.", file=sys.stderr)
        return 1
    alignment = {}
    for label, model_name in ENCODERS.items():
        rows = alignment_rows(model_name)
        mean = float(np.mean([r["alignment_gain"] for r in rows]))
        alignment[label] = {"mean_alignment_gain": mean, "per_class": rows}
        print(f"  {label:8s} mean alignment change {mean:+.4f} over {len(rows)} classes")

    predictions = [{
        "id": f"direction-{label}",
        "claim": (f"On {label}, the per-class alignment change correlates "
                  f"{'positively' if v['mean_alignment_gain'] > 0 else 'negatively'} with the "
                  f"share of available headroom captured."),
        "encoder": label,
        "expected_sign": 1 if v["mean_alignment_gain"] > 0 else -1,
    } for label, v in alignment.items()]
    predictions.append({
        "id": "control-reproduces",
        "claim": (f"The control encoder {CONTROL} reproduces the published within-NACE "
                  f"correlation to within {TOLERANCE}; if it does not, this module is wrong "
                  f"and the other three numbers are withdrawn."),
        "published": published_control(),
        "tolerance": TOLERANCE,
    })

    payload = {
        "study": "encoder_mechanism",
        "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_revision": git_revision(),
        "method_fingerprint": method_fingerprint(),
        "seed": SEED,
        "encoders": ENCODERS,
        "control_encoder": CONTROL,
        "already_known_when_registered": (
            "The corpus-level effect of every encoder here was published before this "
            "registration. No per-class quantity existed for mpnet, LaBSE or bge-m3, and "
            "the predictions are about those."
        ),
        "alignment": alignment,
        "predictions": predictions,
        "note": "Written before any per-class recall on these encoders was computed.",
    }
    PREREGISTRATION.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    for p in predictions:
        print(f"  PREDICTION {p['id']}: {p['claim']}")
    print(f"Wrote {PREREGISTRATION}. Commit it before running the accuracy step.")
    return 0


def evaluate() -> int:
    if not PREREGISTRATION.exists():
        print("No preregistration: run with --preregister and commit the file first.",
              file=sys.stderr)
        return 1
    registered = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    if registered.get("method_fingerprint") != method_fingerprint():
        print("The inputs or the method changed after the prediction was registered; "
              "refusing to test it.", file=sys.stderr)
        return 1

    per_encoder = {}
    for label, model_name in ENCODERS.items():
        rows = registered["alignment"][label]["per_class"]
        recall = recall_rows(model_name)
        stats = correlate(rows, recall)
        stats["mean_alignment_gain"] = registered["alignment"][label]["mean_alignment_gain"]
        stats["mean_recall_gain"] = float(np.mean([recall["rich"][c] - recall["terse"][c]
                                                   for c in recall["terse"]]))
        per_encoder[label] = stats
        print(f"  {label:8s} rho = {stats['rho']:+.3f} (p = {stats['p']:.4f}, "
              f"n = {stats['n_classes']})")

    published = published_control()
    drift = abs(per_encoder[CONTROL]["rho"] - published)
    outcomes = []
    for pred in registered["predictions"]:
        if pred["id"] == "control-reproduces":
            held = drift <= pred["tolerance"]
        else:
            held = np.sign(per_encoder[pred["encoder"]]["rho"]) == pred["expected_sign"]
        outcomes.append({**pred, "held": bool(held)})
        print(f"  {'HELD  ' if held else 'FAILED'} {pred['claim']}")

    payload = {
        "study": "encoder_mechanism",
        "preregistration": PREREGISTRATION.name,
        "registered_at": registered["registered_at"],
        "control_encoder": CONTROL,
        "published_control_rho": published,
        "control_drift": drift,
        "encoders": per_encoder,
        "outcomes": outcomes,
    }
    RESULT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  control drift against the published value: {drift:.4f}")
    print(f"Wrote {RESULT}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregister", action="store_true")
    args = parser.parse_args(argv)
    if not PUBLISHED.exists():
        print("results/predictor_search.json is missing; the control has nothing to "
              "reproduce. Run `make study` first.", file=sys.stderr)
        return 1
    set_seed()
    ensure_dirs()
    return preregister() if args.preregister else evaluate()


if __name__ == "__main__":
    sys.exit(main())
