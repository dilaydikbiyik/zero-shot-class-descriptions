#!/usr/bin/env python3
"""The official German class texts, written by the statistical office, not by us.

    python -m experiments.fetch_official_nace

The paper's main effect is carried by class descriptions this project wrote.
`run_description_source.py` already shows the effect is not an artefact of one
particular writer — an independent 7B model reproduces part of it — but every
arm of that comparison was still written for this study, by a writer who had
seen the corpus. The objection that survives is the simplest one: would the
effect appear with class texts nobody here chose?

Section~\\ref{sec:arxiv} answers it for arXiv, whose category descriptions are
arXiv's own. Nothing answers it for NACE, which is the corpus every headline
figure comes from. This module supplies the missing control: the explanatory
notes of WZ 2008, the German implementation of NACE Rev. 2, published by the
Statistisches Bundesamt. They are in German, the language of the documents, and
they are what a German registrar actually classifies against.

Two arms are written, because the official notes differ from this project's
descriptions in two ways at once and only one of them is the question:

* ``official_full`` — the note verbatim. Externally authored, but also far
  longer: over the nineteen sections that carry one, a median of 78 words
  against this project's 14, and 670 for section C. Authorship and length both
  move.
* ``official_first_sentence`` — the note's first sentence, a median of 19
  words, which is inside this project's own band of 6 to 25. The match is close
  at the median and imperfect in the tail: six sections keep a first sentence
  longer than this project's longest description, the worst being L at 48
  words. The arm narrows the length gap from nearly sixfold to within seven
  words of this project's own descriptions rather than closing it, and what the
  two arms buy is the comparison between them — a length reading of any effect
  has to predict that arms differing nearly sixfold in length behave
  differently.

Two sections, T and U, carry no explanatory note at all. They are recorded as
missing rather than filled with the title, because quietly substituting the
terse name would make the official arm partly a terse arm and flatter whichever
comparison it lost.

Distribution of the text is permitted with attribution: "© Statistisches
Bundesamt, Wiesbaden 2008. Verbreitung, auch auszugsweise, mit Quellenangabe
gestattet." The attribution is carried in the output file.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import urllib.request
import zipfile
from typing import Dict

from experiments.config import DATA_DIR, ensure_dirs

URL = (
    "https://www.klassifikationsserver.de/klassService/thyme/variant/"
    "download/wz2008?file=variant&type=csv"
)
INNER = "Gliederung_mit_Erl"          # the archive member, whose name carries a date
OUT = DATA_DIR / "taxonomy" / "sectors_official.json"
SECTORS_JSON = DATA_DIR / "taxonomy" / "sectors.json"
SECTION_LEVEL = "1"
ATTRIBUTION = (
    "© Statistisches Bundesamt, Wiesbaden 2008. Verbreitung, auch auszugsweise, "
    "mit Quellenangabe gestattet."
)


def download() -> str:
    """The archive, read into memory; nothing is written outside the repository."""
    with urllib.request.urlopen(URL, timeout=120) as response:
        blob = response.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        member = next((n for n in archive.namelist() if INNER in n), None)
        if member is None:
            sys.exit(f"no member matching {INNER!r} in the archive: {archive.namelist()}")
        return archive.read(member).decode("utf-8-sig"), member


def first_sentence(text: str) -> str:
    """The first sentence, kept whole.

    German abbreviations inside these notes ("d. h.", "u. a.", "z. B.") end in a
    full stop, so a split on every period cuts them in half. Only a stop that
    closes a word of more than one letter is treated as a sentence end.
    """
    match = re.search(r"(?<=[a-zäöüß]{2})\.\s", text)
    return text[: match.end()].strip() if match else text.strip()


def parse(payload: str) -> Dict[str, Dict[str, str]]:
    rows = list(csv.reader(io.StringIO(payload), delimiter=";"))
    header = next(
        (r for r in rows if r and r[0].strip() == "Schlüssel WZ 2008"), None
    )
    if header is None:
        sys.exit("the file's header row has changed; parsing stopped rather than guessing")
    at = {name: i for i, name in enumerate(header)}
    start = rows.index(header) + 1

    sections: Dict[str, Dict[str, str]] = {}
    for row in rows[start:]:
        if len(row) <= at["Ebene"] or row[at["Ebene"]] != SECTION_LEVEL:
            continue
        code = row[at["Schlüssel WZ 2008"]].strip()
        note = " ".join(row[at["Einschlüsse"]].split())
        excl = " ".join(row[at["Ausschlüsse"]].split())
        sections[code] = {
            "title": row[at["Titel"]].strip(),
            "official_full": note,
            "official_first_sentence": first_sentence(note) if note else "",
            "official_exclusions": excl,
            "note_words": len(note.split()),
        }
    return sections


def main(argv=None) -> int:
    ensure_dirs()
    payload, member = download()
    sections = parse(payload)

    expected = set(json.loads(SECTORS_JSON.read_text(encoding="utf-8"))["sectors"])
    if set(sections) != expected:
        sys.exit(
            "the official sections do not match this project's: "
            f"missing {sorted(expected - set(sections))}, "
            f"unexpected {sorted(set(sections) - expected)}"
        )

    missing = sorted(c for c, s in sections.items() if not s["official_full"])
    document = {
        "sections": sections,
        "metadata": {
            "source": URL,
            "archive_member": member,
            "attribution": ATTRIBUTION,
            "classification": "WZ 2008, the German implementation of NACE Rev. 2",
            "sections_without_a_note": missing,
            "why": (
                "An externally authored control for the class texts. Every arm of "
                "run_description_source.py was written for this study; these were not."
            ),
            "caveat": (
                "official_full is far longer than this project's descriptions "
                "(median {} words), so it varies authorship and length together; "
                "official_first_sentence varies authorship alone."
            ).format(
                sorted(s["note_words"] for s in sections.values())[len(sections) // 2]
            ),
        },
    }
    OUT.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    words = sorted(s["note_words"] for s in sections.values())
    print(f"{OUT}: {len(sections)} sections")
    print(f"  note length: min {words[0]}, median {words[len(words)//2]}, max {words[-1]} words")
    print(f"  without a note: {missing or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
