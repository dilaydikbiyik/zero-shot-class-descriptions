#!/usr/bin/env python3
"""The sixth and seventh corpora: Turkish, with gold labels nobody here assigned.

    python -m experiments.fetch_turkish            # fetch both corpora into the cache
    python -m experiments.fetch_turkish --summary  # what is in the cache, and its shape

Five corpora so far, two languages, every one of them Indo-European. `TODO.md`
A8 says what that leaves open: whether the alignment account is about
taxonomies or about German. Turkish is agglutinative, so a class name and the
documents it must attract share far less surface form than they do in German or
English, which makes it a harder test than a third Indo-European language.

Two corpora, chosen as a contrast rather than as two replications:

* **MASSIVE (tr-TR)**, 60 intents nested in 18 scenarios. The class names are
  identifiers --- ``alarm_set``, ``qa_factoid`` --- which is the regime NACE and
  Reuters are in, and where the account predicts a definition pays. It also
  carries a real two-level hierarchy with gold labels at both levels, which is
  what A6 says the hierarchy result still needs.
* **TTC-4900**, 7 ordinary readable categories --- ``siyaset``, ``ekonomi``. That
  is the regime 20 Newsgroups and Brown are in, and where the account predicts a
  definition does not pay.

Neither label set was assigned by this project or by a model it ran, which is
the first time that is true of a corpus here other than arXiv.

Two properties of the data are not ideal and are recorded rather than smoothed
over. MASSIVE's documents are single utterances, far shorter than anything
measured so far; document length has never been a variable in this project, so
a MASSIVE result is confounded with that change and TTC-4900 is what separates
them. TTC-4900's text has been normalised by whoever built it --- lowercased,
stripped of punctuation, multiword names joined with underscores --- so it is
not raw Turkish either.

Texts are cached, not redistributed. What this script commits is a manifest of
identifiers, labels and a checksum, so the sample is reproducible with one
network call.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from typing import Dict, List

from experiments.config import DATA_DIR, ensure_dirs

MASSIVE_INTENT_REPO = "mteb/amazon_massive_intent"
MASSIVE_SCENARIO_REPO = "mteb/amazon_massive_scenario"
TTC_REPO = "savasy/ttc4900"
TTC_FILE = "ttc4900/train-00000-of-00001.parquet"
LOCALE = "tr"
# English is fetched as a control on encoder quality, not as a corpus of its
# own: MASSIVE's locales are human-localised parallel data, so the same content
# appears in both and the comparison carries no translator. See
# docs/turkish_phase.md, "Turkish is the subject; English is its control".
CONTROL_LOCALE = "en"
SPLITS = ("train", "validation", "test")

CACHE = DATA_DIR / "cache"
MASSIVE_CACHE = CACHE / "massive_tr.json"
MASSIVE_EN_CACHE = CACHE / "massive_en.json"
TTC_CACHE = CACHE / "ttc4900.json"
MANIFEST = DATA_DIR / "external" / "turkish_manifest.json"

# TTC-4900 ships its categories as integers. The mapping is the dataset card's.
TTC_CATEGORIES = {
    0: "siyaset",
    1: "dunya",
    2: "ekonomi",
    3: "kultur",
    4: "saglik",
    5: "spor",
    6: "teknoloji",
}


def _require_hub():
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:  # pragma: no cover - exercised only without the dep
        sys.exit(
            "huggingface_hub is needed to fetch these corpora.\n"
            "    pip install -r requirements.txt"
        )
    return hf_hub_download


def fetch_massive(locale: str = LOCALE) -> List[Dict]:
    """MASSIVE for one locale, intent and scenario joined on the utterance id."""
    hf_hub_download = _require_hub()

    def read(repo: str) -> Dict[str, Dict]:
        rows: Dict[str, Dict] = {}
        for split in SPLITS:
            path = hf_hub_download(
                repo, f"{split}/{locale}.json.gz", repo_type="dataset"
            )
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                for line in fh:
                    row = json.loads(line)
                    rows[str(row["id"])] = {
                        "text": row["text"],
                        "label": row["label"],
                        "split": split,
                    }
        return rows

    intents = read(MASSIVE_INTENT_REPO)
    scenarios = read(MASSIVE_SCENARIO_REPO)

    records = []
    for uid, intent in sorted(intents.items(), key=lambda kv: int(kv[0])):
        scenario = scenarios.get(uid)
        if scenario is None or scenario["text"] != intent["text"]:
            # The two repositories are split the same way; a mismatch would mean
            # the join is wrong, and a wrong join is worse than a missing row.
            continue
        records.append(
            {
                "id": uid,
                "text": intent["text"],
                "intent": intent["label"],
                "scenario": scenario["label"],
                "split": intent["split"],
            }
        )
    return records


def fetch_ttc() -> List[Dict]:
    """TTC-4900, as published: one parquet file, integer categories."""
    hf_hub_download = _require_hub()
    import pandas as pd

    path = hf_hub_download(TTC_REPO, TTC_FILE, repo_type="dataset")
    frame = pd.read_parquet(path)
    records = []
    for i, row in frame.iterrows():
        category = TTC_CATEGORIES.get(int(row["category"]))
        if category is None:
            continue
        records.append(
            {"id": str(i), "text": str(row["text"]).strip(), "category": category}
        )
    return records


def _digest(records: List[Dict]) -> str:
    payload = json.dumps(records, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write(path, records: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def summarise() -> Dict:
    out: Dict[str, Dict] = {}
    if MASSIVE_CACHE.exists():
        rows = json.loads(MASSIVE_CACHE.read_text(encoding="utf-8"))
        out["massive"] = {
            "documents": len(rows),
            "intents": len({r["intent"] for r in rows}),
            "scenarios": len({r["scenario"] for r in rows}),
            "mean_words": round(
                sum(len(r["text"].split()) for r in rows) / max(len(rows), 1), 2
            ),
        }
    if MASSIVE_EN_CACHE.exists():
        rows = json.loads(MASSIVE_EN_CACHE.read_text(encoding="utf-8"))
        out["massive_en_control"] = {
            "documents": len(rows),
            "mean_words": round(
                sum(len(r["text"].split()) for r in rows) / max(len(rows), 1), 2
            ),
        }
    if TTC_CACHE.exists():
        rows = json.loads(TTC_CACHE.read_text(encoding="utf-8"))
        out["ttc4900"] = {
            "documents": len(rows),
            "categories": len({r["category"] for r in rows}),
            "mean_words": round(
                sum(len(r["text"].split()) for r in rows) / max(len(rows), 1), 2
            ),
        }
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--summary", action="store_true", help="report what is cached and stop"
    )
    args = parser.parse_args(argv)

    ensure_dirs()
    if args.summary:
        print(json.dumps(summarise(), ensure_ascii=False, indent=2))
        return 0

    massive = fetch_massive(LOCALE)
    massive_en = fetch_massive(CONTROL_LOCALE)
    ttc = fetch_ttc()
    _write(MASSIVE_CACHE, massive)
    _write(MASSIVE_EN_CACHE, massive_en)
    _write(TTC_CACHE, ttc)

    manifest = {
        "massive": {
            "repositories": [MASSIVE_INTENT_REPO, MASSIVE_SCENARIO_REPO],
            "locale": LOCALE,
            "control_locale": CONTROL_LOCALE,
            "splits": list(SPLITS),
            "documents": len(massive),
            "documents_control": len(massive_en),
            "sha256": _digest(massive),
            "sha256_control": _digest(massive_en),
            "licence": "CC BY 4.0",
        },
        "ttc4900": {
            "repository": TTC_REPO,
            "file": TTC_FILE,
            "documents": len(ttc),
            "sha256": _digest(ttc),
            "categories": TTC_CATEGORIES,
        },
    }
    _write(MANIFEST, manifest)
    print(json.dumps(summarise(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
