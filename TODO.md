# TODO

What is done, what is open, and what is deliberately not being done. Updated as
work lands; every claim here points at the file that settles it.

**Where the project stands.** Six evaluation sets, 12,341 documents, 108
classes. Nine preregistered studies, 40 predictions committed to version control
before they were measured, 33 held and the seven failures published. 72
comparisons corrected together with Holm (45 nominal, 32 surviving). The advice
the work supports is collected in `docs/recipe.md`, with a measured budget, a
measured price for getting it wrong, and an abstention curve. 214 tests in CI,
paper body at the 8-page limit. Submitted to ARR on 12 October 2026 as
submission 6377; the version that was uploaded is pinned at tag
`v1-arr-october-2026` and described in `docs/submission_v1.md`. **That
submission was desk rejected on 27 October 2026 without being reviewed**: it
went into the lottery pool because no service contributor was nominated, and
was not drawn. The letter states that the decision "is not an assessment of
your paper" and that it is without prejudice. Nothing about the evidence
changed; what changed is that the paper is no longer under review anywhere.

---

## A. Open research gaps, ranked

Each item says what a reader could do afterwards that they cannot do now. That
is the test for whether it belongs in a paper rather than in a backlog.

### ~~A1. The quantity, estimated without labels~~ — **done, and it held**
All four registered predictions held. The estimate, which uses no label
anywhere, tracks the labelled quantity at ρ = +0.818 over 102 classes and
predicts the share of headroom captured at ρ = +0.564 (p = 6e-10, surviving
Holm) against +0.670 for the labelled version. It degrades where the
pseudo-assignment is poorest — on NACE, +0.201 against +0.759 — so the advice it
licenses is: where the terse classifier is already somewhat right, an unlabelled
sample tells you whether rewriting pays at all. It does not license an order to
work in; see the rewrite-priority simulation. `make labelfree`,
`results/labelfree_predictor.json`, paper §*The quantity, without labels*.
**Still open from it:** a threshold rule with a measured false-positive rate,
i.e. "how large must the estimate be before rewriting is worth the effort".

### ~~A2. Why alignment is the right quantity~~ — **done**
The derivation is in the paper: the decision is an argmax over cosines, so what
moves a document is the margin between its own class and the nearest competitor;
moving a class vector toward its centroid raises the first term for all of that
class's documents and lowers the second for its neighbours'. The simulation
confirms both halves — accuracy monotone in the distance moved at all four
separations, and moving one vector onto its own centroid gains that class +0.550
of recall while costing its nearest neighbour −0.012 and everyone else +0.001,
falling to +0.025 as the classes crowd together. `make synthetic`,
`results/synthetic.json`.
**Still open:** the derivation is informal. A bound rather than an argument —
expected margin change as a function of Δa and the neighbour distances — would
be stronger, and is a theory exercise rather than a measurement.

### ~~A3. How much writing is enough~~ — **done**
Twenty words, on both German sets: name only 29.4%, +10 words 47.5%, **+20
55.5%**, +40 52.8%. Ninety per cent of the gain arrives by twenty words and the
curve then turns slightly down, which matches the negative correlation between
words added and per-class gain. `make dose-response`.

### ~~A4. What a wrong description costs~~ — **done**
A quarter of the classes given another class's definition costs 4.7 points at
random and 12.7 when the swap happens between the classes already most similar;
a generic text of the same length as the definitions lands within three points of
the name-only floor. So length is not the active ingredient, and the pairs worth
checking are the ones that already look alike. `make description-noise`.

### ~~A5. A written recipe~~ — **done**
`docs/recipe.md`: seven sections, every claim pointing at the result that
carries it, including the three things it explicitly does not tell you (depth
beyond one hierarchy level, prompted models, and languages other than German and
English).

### A6. Hierarchy — *partly done; the real test still needs labels*
20 Newsgroups has two levels for free, and they behave the same way: the
identifier→name step pays at 20 classes (+10.0) and at the 6 groups they form
(+13.4), and the name→definition step at neither (+0.4, +1.3). So the quantity is
the distance between class text and document vocabulary rather than the number of
classes. `make hierarchy`.
**Still open:** NACE four digits down, which needs labels at that depth — the one
part of this that no amount of compute substitutes for.

### ~~A7. Abstention~~ — **done**
The margin the decision already computes prices it: Top-1 is 55.4% at 90%
coverage, 58.9% at 75%, 65.3% at 50% and 76.0% at 25%. Reaching 80% means handing
back all but 23% of the documents, which is the honest shape of the trade-off on
a task whose labels agree with a human 80% of the time. `make abstention`.

### A8. Breadth: another language, another taxonomy — *open, and the only one that needs data*
German and English; NACE, Reuters, 20NG, Brown, arXiv. A second language with
gold labels (NACE is published in 24) or another gold-labelled taxonomy
(EuroVoc, DDC, MASSIVE) would test whether the account is about taxonomies or
about German. Every other gap on this list was closed with the corpora already
here; this one cannot be, because it needs labelled documents in a language
nobody has labelled for us. It also needs a new dependency to fetch them, which
is a decision for after the submission rather than before it.
**Now being closed.** The design is written down in
[`docs/turkish_phase.md`](docs/turkish_phase.md), before the data is on disk:
Turkish, MASSIVE (tr-TR) and TTC-4900, with six predictions to register and a
fourth description-writer arm — a native speaker — that no earlier study has.
Turkish NACE was the first choice and is ruled out on **access, not method**:
the gazette's announcement texts sit behind a login, MERSİS publishes no bulk
download or public API, and TÜİK's firm-level query is not public. Recorded so
it is not reopened without one of those three changing.

**Afterwards:** the claim is about zero-shot classification, not about one task.

---

## B. Mine to finish before submission

- [x] Anonymous archive: the anonymiser no longer carries the strings it removes
      (`private/identity.txt`, untracked, with a test that scans the archive).
- [x] Cost measured, and the ordering verified on a second device.
- [x] Two open LLM baselines from two families, with the harness defect that the
      first run of the second one measured instead of the model.
- [x] The research page republished with the current record (14 entries).
- [x] The two stale pages brought up to date, and a decision recorded about
      them: the GitHub Pages research record is the only one meant to be
      public. The readiness review was deleted on 4 October 2026 once every
      gap it listed had closed — `docs/paper_readiness.md` carries the same
      material, versioned. The Turkish defence notebook stays, private and
      unlinked; it is interview preparation and not part of the record.
- [x] A2 and A5, plus A3, A4, A6 and A7 — every gap that did not need new
      labels or a new dependency is closed.
- [x] The findings turned into something a stranger can run on their own
      taxonomy: `experiments/diagnose.py`, with every figure it quotes read out
      of `results/` at run time rather than typed into it, and
      `run_overlap_estimate` measuring what its regime check costs when it has
      no labels to group by. The guide in `docs/recipe.md` now opens with the
      procedure instead of ending with the findings.
- [x] The description effect tested on a modern encoder, after a review
      objected that the three in the paper are an older generation. `bge-m3`
      replicates the content effect at +17.7 points and the language contrast
      stays negative there too. Both new tests joined the hypothesis family and
      the whole family was corrected again, 72 tests with 32 surviving — the
      point is that they were corrected together, not that the old results
      happened to survive.
      *Still open:* this replicates the **effect**, not the mechanism. The
      per-class Δa-against-gain correlation was not computed on `bge-m3`, so
      the encoder-independence of the quantity itself rests on the three
      encoders already reported.
- [x] The label-free estimate tested as a decision rule, not only as a
      correlation, after a review pointed out that the paper promised the first
      and measured the second. Rewriting only the classes it ranks highest
      captures about what a random order captures; with labels the same
      quantity captures half the gain from a tenth of the classes. The paper,
      the guide and the diagnostic all now say this, and three tests hold the
      negative in place.
- [x] Body page count rechecked against the right boundary. The earlier "eight
      pages" was measured to `\appendix`, which falls after the bibliography;
      measured to the start of Limitations, which is what ARR counts, the body
      ran to nine. Related Work, the error analysis, the retired-pipeline
      ablation and the cost subsection were compressed; it now ends on page
      eight with every citation intact.

## C. Yours, and nobody else can do them

- [x] **OpenReview account** — approved, and the submission went in under it.
      The profile itself is still thin; OpenReview asks for it to be complete
      within a week of submitting, so by about 20 October.
- [x] **CV numbers** — done 8 October: the industry CV now reads 207 tests, nine
      preregistered studies, 33 of 40 predictions held, six evaluation sets and
      12,341 documents, and every project carries a repository link that was
      checked unauthenticated. The research variant still carries the old
      figures and a venue that has not been decided. The 207 has since drifted
      too: the suite is at 214. Not worth a reprint on its own — fold it in the
      next time the CV is edited for another reason.
- [ ] **The research CV still carries the old figures**, and a target venue that
      has not been decided. It says three preregistered studies, 12 of 15, 46
      comparisons and 106 tests; the true numbers are nine, 33 of 40, 72 and 214.
      Its *Research* blurb also names ACL SRW as the target, which is not the
      decision. Two reminders when you update it: the word TF-IDF baseline is
      44.5% and the character n-gram one 54.2% — different systems, often
      conflated; and lead with six evaluation sets and 12,341 documents rather
      than with 299.
- [x] **Pin the submitted version** — done 12 October. The order matters, because the tag has to
      mark the commit the uploaded files were built from, not the later commit
      that stores the record:

      1. `make submission` — build the PDF and archive from the current commit
      2. Upload that exact PDF; do not rebuild it afterwards
      3. `make submission-record VENUE="ARR October 2026" TAG=v1-arr-october-2026`
      4. `git tag -a v1-arr-october-2026 -m "Submitted to ARR, October 2026"`
         — at this commit, which is the one the record names
      5. Commit `docs/submission_v1.md` on top; this does not invalidate it,
         because the record says which commit it describes
      6. `python tools/submission_record.py --verify docs/submission_v1.md`
      7. `git push && git push --tags`

      Step 6 fails if the PDF was rebuilt after step 3, or if the tag points
      anywhere but the commit named in the record. It ran clean: the remote tag
      dereferences to `f179d0d`, which is the commit the record names and the
      one the uploaded PDF was built from. Keep the OpenReview submission
      confirmation too: it is the one timestamp neither the record nor the tag
      can forge. Everything after it is post-submission work and gets its own
      preregistrations; nothing is written back into the ones already in
      `results/`.
- [x] **Submitted to ARR**, 12 October 2026, submission 6377.
- [x] **Service contributor — this is what cost the cycle.** The October 2026
      cycle was the first under ACL's sustainable reviewing policy: a submission
      that names no qualified contributor is not reviewed on its merits but
      placed in a lottery for whatever capacity remains. 6377 was placed there
      and not drawn. The field was not present in the submission form on
      12 October — the revision history shows it first appearing as an empty
      field in a venue-side post-submission edit on 13 October at 15:32 — but
      the outcome is the same either way, and the rule is now known.
      **Next time the order is: arrange the contributor first, submit second.**
      The submission form opens about two weeks before the deadline, and the
      contributor must file their own registration form within 48 hours of it.
      A contributor need not be a co-author, but they must be qualified to
      review, have a complete OpenReview profile, and accept that their own
      submissions are desk rejected if they do not serve.
- [ ] **The route that needs nobody: qualify yourself.** ARR allows manual
      verification for authors who lack the publication count but have a record
      of reviewing or secondary reviewing at ARR. Signing up for that pool now
      and building the record over a cycle or two makes you eligible to be your
      own contributor, which is the only arrangement that does not depend on
      someone else's goodwill. For a sole author this is the structural fix,
      not a workaround.
- [ ] **arXiv preprint.** The source package builds and is ready
      (`main.tex` with `\usepackage[preprint]{acl}`, `main.bbl`, `acl.sty`,
      `acl_natbib.bst`, `references.bib` and the fifteen table files; 18 pages,
      no unresolved citations). It is blocked on one thing only: cs.CL requires
      an **endorsement** for a first-time submitter, requested 12 October.
      Primary category `cs.CL`, cross-list `cs.LG`, licence CC BY 4.0 to match
      OpenReview. Nothing about the evidence depends on this — the submission
      record and the tag are the timestamp; arXiv adds reach, not record. The
      desk rejection removes the last reason to wait: the paper is under review
      nowhere, so no anonymity or dual-submission rule applies to it now.
- [ ] **Read the paper end to end**, and look at the pages as well as the words.
      Three appendix tables were printing over each other until you noticed it in
      the PDF; a test now catches that class of defect, but only the kinds it was
      taught. Every sentence has to be defensible by you;
      the defence notebook exists for this.
- [ ] **No longer optional — this is what the next cycle is for.** The delay
      bought a window, and the three things in it are the ones reviewers would
      have pressed hardest on:

      1. **A German second annotator** for the 50-document blind sample
         (`make second-annotator`, `docs/second_annotator.md`). This closes the
         largest stated gap: the labels are model-assisted and only the author
         has verified them, so no human–human agreement exists anywhere in the
         paper.
      2. **The official NACE explanatory notes as an externally authored
         control condition.** It answers the objection that the descriptions
         carrying the main effect were written by the author, and the source
         study already shows the effect is corpus knowledge rather than
         authorship.
         *Done, as far as it can go without the author:* `make
         official-nace-fetch` fetches the WZ 2008 explanatory notes — the
         German implementation of NACE Rev. 2, written by the Statistisches
         Bundesamt in 2008 — into `data/taxonomy/sectors_official.json`, in the
         documents' own language and with attribution.
         `make official-nace-preregister` then registers the prediction and
         `make official-nace` tests it (`experiments/run_official_nace.py`,
         `docs/official_nace.md`).
         Four arms: the terse control and the assistant's definitions, which
         the description-source study also uses, plus the official note
         verbatim (median 78 words over the nineteen sections that carry one,
         670 for section C) and its first sentence (median 19, against this
         project's own 6–25). The official text enters twice because a single
         external arm would vary authorship and length together; the two arms
         differ by nearly a factor of six in length and not at all in
         authorship, so a length reading of any effect has to predict they
         diverge.
         Sections T and U carry no official note. They are recorded as missing
         rather than filled with their title, and dropped from the label space
         of **all four** arms, so every arm faces the same 19-way problem. No
         document is lost — the labelled set covers 18 sections and neither T
         nor U is among them — but the accuracies are 19-way and so not
         comparable to the paper's 21-way figures, which is why the control is
         re-run inside the study.
      3. **Code 50 errors blind** — the coding tool is in your Downloads.

      Each gets its own preregistration; none of it is written back into the
      registrations already in `results/`, and `v1-arr-october-2026` stays as
      the record of what was submitted in October.
- [ ] **Rename the repository to `class-description-effect`** — *after your
      internship applications resolve*, so no application points at a dead link.
      When you rename it on GitHub, the seven files that hardcode the old name,
      `CITATION.cff`, the README badges, the Pages URL and the research page's
      sentence about the repository keeping its original name all get fixed in
      one commit.

## D. Deliberately not doing, and why

- **Replacing the 299-document evaluation set.** Every preregistered prediction
      was committed against that exact set; swapping its documents would destroy
      the evidence that the predictions came first. *Adding* sets is a different
      thing and has been done twice: 7,470 arXiv abstracts with gold labels, and
      a second German set of 1,200 documents with its own registered
      predictions. What stays true is that only 50 documents anywhere in this
      project carry a human-verified label.
- **Chasing 90%+ Top-1.** The labels themselves agree with a human on 80% of a
      blind sample (κ = 0.772), and 48% of coded errors are documents with more
      than one defensible answer, which puts the single-label ceiling near 77%.
      A system scoring 95% against these labels would be fitting the labeller.
      Top-3 (81.6%) is the number the intended use cares about.
- **Tuning prompts or hyperparameters until the numbers look better.** The
      Rocchio setting stayed untuned and got a sensitivity grid instead; the
      degenerate LLM run was diagnosed, not retried until it flattered us.
- **FastAPI, Docker, AWS, MLflow, monitoring.** Good for an engineering
      portfolio, irrelevant to a paper, and they would consume the days before
      the deadline. Revisit after submission.
- **A paid API baseline.** The adapter is released and unrun; it must not be a
      Claude model, which produced the labels and would be graded on its own
      answers.

## E. Dates

| | |
| --- | --- |
| ARR submission | 12 October 2026 — done, submission 6377 |
| OpenReview profile complete | done, with ORCID |
| Service contributor | **not nominated — this is what ended the cycle** |
| Desk rejected: lottery, without prejudice | **27 October 2026** |
| Next ARR cycle | not yet published; ACL 2027's ARR deadline is listed as January 2027 |
| ISARC Marmara abstract, 12th congress | **18 December 2026** — no longer blocked |

Checked against <https://aclrollingreview.org/dates> on 27 October 2026; the
cycles after October 2026 were not listed there yet. The October review dates —
reviews 16 November, response 24–30 November, meta-reviews 17 December — no
longer apply to this paper.

Two things the desk rejection released rather than cost: the ISARC abstract was
waiting for 17 December only because ARR forbids submitting elsewhere during
review, and the arXiv preprint never depended on ARR at all. Both are free now.
