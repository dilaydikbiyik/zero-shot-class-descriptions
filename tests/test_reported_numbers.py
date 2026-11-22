"""
Every number quoted in the README, the readiness report and the paper must
match results/. A figure that is correct in results/ and stale in the prose is
the failure mode this project has already hit twice; this makes it a test
failure instead of something a reader finds.

Run with: pytest tests/test_reported_numbers.py -v
"""

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load(name):
    path = RESULTS / f"{name}.json"
    if not path.exists():
        pytest.skip(f"{path.name} not generated yet — run `make reproduce` and `make study`")
    return json.loads(path.read_text(encoding="utf-8"))


def system(results, key):
    return next(s for s in results["systems"] if s["key"] == key)


def pct(value):
    return f"{value * 100:.1f}%"


DOCS = {
    "README.md": ROOT / "README.md",
    "docs/paper_readiness.md": ROOT / "docs" / "paper_readiness.md",
    # The project page is the one artefact a reader is most likely to see and
    # least likely to cross-check, so it is held to the same standard.
    "docs/index.html": ROOT / "docs" / "index.html",
}


def claims():
    """(source, formatted figure) pairs the prose is required to agree with."""
    baselines = load("baselines")
    ablation = load("ablation")
    study = load("description_study")
    search = load("predictor_search")
    reuters = load("reuters")
    news = load("replication_20newsgroups")

    ours = system(baselines, "full")["sector"]
    tfidf = system(baselines, "tfidf-nace")["sector"]
    no_seeds = next(s for s in ablation["systems"] if s["key"] == "no-seed-vector")["sector"]
    old_taxonomy = next(s for s in ablation["systems"] if s["key"] == "taxonomy-v1")["sector"]

    return [
        ("headline Top-1", pct(ours["top1_accuracy"])),
        ("headline Top-3", pct(ours["top3_accuracy"])),
        ("TF-IDF Top-1", pct(tfidf["top1_accuracy"])),
        ("previous taxonomy Top-1", pct(old_taxonomy["top1_accuracy"])),
        ("no-seeds Top-1", pct(no_seeds["top1_accuracy"])),
        ("description study, terse", pct(list(study["conditions"].values())[0]["top1_accuracy"])),
        ("description study, translated", pct(list(study["conditions"].values())[1]["top1_accuracy"])),
        ("description study, rewritten", pct(list(study["conditions"].values())[2]["top1_accuracy"])),
        ("content effect", f"{study['content_effect']['gain_pp']:+.1f}".replace("+", "+")),
        ("alignment rho", f"{search['correlations']['alignment_gain']['rho']:+.3f}".replace("+", "+")),
        ("Reuters elaboration gain", f"{reuters['defining_the_class']['gain_pp']:+.1f}"),
        ("20NG elaboration gain", f"{news['defining_the_class']['gain_pp']:+.1f}"),
    ]


@pytest.mark.parametrize("doc", sorted(DOCS))
def test_prose_quotes_only_current_numbers(doc):
    """Each headline figure appears in the prose exactly as results/ has it."""
    text = DOCS[doc].read_text(encoding="utf-8")
    missing = []
    for label, figure in claims():
        # A figure may legitimately be absent from a given document; what must
        # never happen is the document quoting a *different* value for it.
        stripped = figure.lstrip("+")
        if stripped not in text:
            missing.append((label, figure))
    # The README carries every headline; the readiness report carries all of them too.
    assert not missing, (
        f"{doc} does not quote these current figures — it is probably still "
        f"showing an earlier run: {missing}"
    )


def test_no_superseded_headline_survives():
    """The two numbers this project has already had to correct in public."""
    for doc, path in DOCS.items():
        text = path.read_text(encoding="utf-8")
        for stale, why in (
            ("80.0%", "the accuracy measured on the retired hand-written evaluation set"),
            ("36.1%", "the headline before the taxonomy was rewritten"),
        ):
            for line in text.splitlines():
                low = line.lower()
                # The same digits appear as an inter-annotator agreement rate,
                # which is a different quantity entirely.
                if any(w in low for w in ("agreement", "κ", "kappa", "confidence", "pilot")):
                    continue
                if stale in line:
                    # Mentioning the old number while explaining it is fine;
                    # quoting it as a current result is not.
                    assert any(
                        marker in line.lower()
                        for marker in ("old", "previous", "earlier", "before", "was", "retired", "reported")
                    ), f"{doc} quotes {stale} ({why}) without marking it as superseded:\n  {line.strip()}"


def test_paper_hardcodes_no_figures():
    """The paper cites macros, never literal numbers."""
    import re

    tex = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    body = tex.split(r"\begin{document}", 1)[1]
    # A comment starts at an unescaped %; "\%" is a literal percent sign and
    # stripping it as a comment would hide every hardcoded percentage.
    body = re.sub(r"(?<!\\)%.*", "", body)
    body = re.sub(r"\\(?:label|ref|cite[pt]?|input|documentclass|usepackage)\{[^}]*\}", "", body)
    # "p < 0.001" is a threshold, not a result, and is the one form allowed.
    body = re.sub(r"p\s*<\s*0\.001", "", body)
    # The Reuters collection's README asks to be cited by this exact name; the
    # "1.0" in it is a release number, not a result.
    body = body.replace("Distribution 1.0", "")
    # Any percentage (with or without decimals), any signed or unsigned decimal,
    # and any "N points" figure. Years and small design counts are integers
    # without a unit and are not results, so they are not matched.
    patterns = [
        r"(?<![\\{\w.])\d+(?:\.\d+)?\\%",
        r"(?<![\\{\w.])[-+]?\d+\.\d+",
        r"(?<![\\{\w.])\d+(?:\.\d+)?~?\s?points",
    ]
    offenders = [hit for pattern in patterns for hit in re.findall(pattern, body)]
    assert not offenders, (
        "paper/main.tex hardcodes figures instead of using macros from "
        f"tables/macros.tex: {sorted(set(offenders))}"
    )


def holm_family_size() -> int:
    """How many comparisons the correction runs over, as results/ has it."""
    return int(load("effect_sizes")["n_tests"])


# "77 comparisons" can only ever mean the corrected family. "77 tests" can also
# mean the test suite, so that spelling is only checked where the sentence is
# about the correction.
FAMILY_PATTERNS = (
    re.compile(r"(\d+)\s+comparisons"),
    re.compile(r"(\d+)\s+tests"),
)
CORRECTION_WORDS = ("holm", "corrected", "correction")


@pytest.mark.parametrize("doc", sorted(DOCS))
def test_the_corrected_family_size_is_current(doc):
    """The family grows whenever a study is added, and every sentence that
    quotes its size has to grow with it.

    This is the drift that actually happened: a study was added, the family
    went from 72 comparisons to 77, and four sentences across three documents
    went on quoting 72 — one of them 62, from an even earlier run. Nothing
    caught it, because each sentence was written by hand and no number in it is
    derived from results/.
    """
    expected = holm_family_size()
    lines = DOCS[doc].read_text(encoding="utf-8").splitlines()
    wrong = []
    for i, line in enumerate(lines):
        context = (lines[i - 1] + " " + line).lower() if i else line.lower()
        for pattern in FAMILY_PATTERNS:
            if pattern is FAMILY_PATTERNS[1] and not any(w in context for w in CORRECTION_WORDS):
                continue
            for found in pattern.finditer(line):
                if int(found.group(1)) != expected:
                    wrong.append((i + 1, found.group(0)))
    assert not wrong, (
        f"{doc} quotes a stale size for the corrected family; results/ says "
        f"{expected} comparisons: {wrong}"
    )


def test_the_readme_quotes_the_real_test_count():
    """The README states how many tests there are, and that number drifts every
    time a test is added -- it has already drifted twice. Collection is cheap,
    so the claim is checked against the suite itself rather than maintained by
    hand."""
    import subprocess
    import sys

    harness = {"test_experiments.py", "test_official_nace.py", "test_turkish.py",
               "test_reported_numbers.py"}
    counts = {}
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        out = subprocess.run([sys.executable, "-m", "pytest", str(path), "-q", "--collect-only"],
                             capture_output=True, text=True, cwd=ROOT).stdout
        found = re.search(r"(\d+) tests? collected", out)
        counts[path.name] = int(found.group(1)) if found else 0
    total = sum(counts.values())
    in_harness = sum(n for name, n in counts.items() if name in harness)
    claim = (f"{total} tests: {in_harness} covering the experiment harness, "
             f"{total - in_harness} covering the pipeline.")
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert claim in text, f"README should say: {claim}"
