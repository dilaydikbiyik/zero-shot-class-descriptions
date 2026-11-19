#!/usr/bin/env python3
"""Arm 4: the class definitions written by a native speaker.

    python -m experiments.native_descriptions --export   # a sheet to fill in
    python -m experiments.native_descriptions --merge    # put it back, with checks

`run_description_source.py` compares three writers — a terse control, this
project's assistant, and an independent 7B model. None of them is a person
writing in their own language, and the main effect of the paper rests on class
texts the assistant wrote. If a native speaker writes a much better class text
than the assistant does, part of that effect is an artefact of who happened to
be available to write, and the paper should say so. That is prediction P6 of
`docs/turkish_phase.md`, and it is registered because it may well fail.

The sheet deliberately carries the class name and nothing else. It does not
carry a document, an example utterance, a count or an error, because a
definition written after seeing those is tuned to the evaluation rather than
written from the class, and would win for a reason that has nothing to do with
the account being tested.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Dict

from experiments.config import DATA_DIR, RESULTS_DIR, ensure_dirs

CLASSES_JSON = DATA_DIR / "taxonomy" / "turkish_classes.json"
SHEET = RESULTS_DIR / "turkish_native_descriptions.csv"
COLUMNS = ("corpus", "class", "identifier", "terse_tr", "definition_native_tr")


def _load() -> Dict:
    return json.loads(CLASSES_JSON.read_text(encoding="utf-8"))


def export() -> int:
    ensure_dirs()
    doc = _load()
    rows = []
    for corpus in (c for c in doc if c != "metadata"):
        for key in sorted(doc[corpus]):
            entry = doc[corpus][key]
            rows.append(
                {
                    "corpus": corpus,
                    "class": key,
                    "identifier": entry["identifier"],
                    "terse_tr": entry["terse_tr"],
                    "definition_native_tr": entry.get("definition_native_tr", ""),
                }
            )
    with SHEET.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    done = sum(1 for r in rows if r["definition_native_tr"])
    print(f"{SHEET}: {len(rows)} classes, {done} already written, {len(rows) - done} to go")
    print("Write one Turkish definition per row, from the class name alone.")
    return 0


def merge() -> int:
    if not SHEET.exists():
        sys.exit(f"{SHEET} is not there. Export it first:\n"
                 "    python -m experiments.native_descriptions --export")
    doc = _load()
    with SHEET.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    written, problems = 0, []
    for row in rows:
        corpus, key = row["corpus"], row["class"]
        if corpus not in doc or key not in doc[corpus]:
            problems.append(f"unknown class {corpus}/{key}")
            continue
        text = (row.get("definition_native_tr") or "").strip()
        if not text:
            continue
        entry = doc[corpus][key]
        if text == entry["definition_assistant_tr"]:
            problems.append(f"{corpus}/{key}: identical to the assistant's definition")
            continue
        if len(text) <= len(entry["terse_tr"]):
            problems.append(f"{corpus}/{key}: not longer than the terse name")
            continue
        entry["definition_native_tr"] = text
        written += 1

    if problems:
        for p in problems:
            print(f"  ! {p}")
        sys.exit(f"{len(problems)} problem(s); nothing was written.")

    total = sum(len(doc[c]) for c in doc if c != "metadata")
    CLASSES_JSON.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"merged {written} of {total} definitions into {CLASSES_JSON}")
    if written < total:
        print(f"{total - written} still empty; the arm stays out of the study until all are written.")
    else:
        print("Arm 4 is complete. Next: make turkish-preregister")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", action="store_true", help="write the sheet")
    group.add_argument("--merge", action="store_true", help="read it back, with checks")
    args = parser.parse_args(argv)
    return export() if args.export else merge()


if __name__ == "__main__":
    raise SystemExit(main())
