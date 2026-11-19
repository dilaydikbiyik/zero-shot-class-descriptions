# The Turkish phase — design, written before the data

This document fixes the design of the next study before any of its data is on
disk. It exists for the same reason the preregistration files in `results/`
exist: a prediction is only worth something if it was written down while it
could still turn out wrong.

Nothing here is a result. No accuracy figure appears in this file, and none
should be added to it later; results go to `results/` and the paper, as before.

## The gap this closes

`TODO.md` A8 is the only open gap that cannot be closed with the corpora
already in the repository:

> German and English; NACE, Reuters, 20NG, Brown, arXiv. A second language with
> gold labels … would test whether the account is about taxonomies or about
> German.

Five corpora, two languages, and every one of them Indo-European. If the
alignment account is about taxonomies, a third language with a different
morphology should behave the same way. If it is about German, it should not.
Turkish is agglutinative, which makes it a harder test than a third
Indo-European language would be, and that is the point of choosing it.

A second gap is touched rather than closed. A6 says the hierarchy result rests
on 20 Newsgroups' two levels and that the real test needs gold labels at depth.
MASSIVE ships a two-level hierarchy — 18 scenarios above 60 intents — with
gold labels at both levels, so the same measurement can be repeated on a
taxonomy that was not built by this project.

## What was ruled out, and why

**Turkish NACE.** This was the first choice and it is the scientifically
strongest one: the same taxonomy, the same genre of document, a different
language, and registry-assigned labels rather than annotator-assigned ones.
Turkish company registrations do carry an official NACE code, assigned at
registration under the Ticaret Sicili Yönetmeliği and recorded in the TOBB
common database and TÜİK's business register.

It is ruled out on access, not on method. The gazette's announcement texts are
behind a login (`ticaretsicil.gov.tr` → İlan Görüntüleme → *"GİRİŞ YAPMALISINIZ"*),
MERSİS publishes no bulk download or public API, and TÜİK's firm-level query is
not public. Collecting even 300 documents would mean opening them one at a time
behind that login, which neither scales nor rests on firm ground with respect to
the site's terms. Recorded here so the question is not reopened later: the
obstacle is access, and it has not changed unless one of those three things does.

## The corpora

| Corpus | Documents | Classes | Class names | Licence |
| --- | --- | --- | --- | --- |
| MASSIVE (tr-TR) | 16,521 utterances | 60 intents over 18 scenarios | identifier-like (`alarm_set`) | CC BY 4.0 |
| TTC-4900 | 4,900 news documents | 7 | readable (`siyaset`, `ekonomi`, …) | see dataset card |

The two are chosen as a contrast, not as a pair of replications. MASSIVE's
class names are identifiers, which is the regime NACE and Reuters are in, and
where the account predicts a definition pays. TTC-4900's are ordinary readable
words, which is the regime 20 Newsgroups and Brown are in, and where the account
predicts it does not. A study that predicts a gain in one and no gain in the
other, in advance, is worth more than two studies that each predict a gain.

One difference from everything measured so far has to be stated plainly:
MASSIVE's documents are single utterances, far shorter than a trade-register
purpose or a news article. Document length has never been varied in this
project — the dose-response result concerns the length of the *class text*, not
the document. Whatever MASSIVE shows is therefore confounded with that change,
and TTC-4900, whose documents are ordinary articles, is what separates the two.

## Turkish is the subject; English is its control

Why not simply use another English corpus: English is already in the evidence
base four times over (Reuters, 20 Newsgroups, Brown, arXiv). A fifth English
corpus would be another taxonomy, which is the weaker half of what A8 asks for,
and no new language at all.

Turkish carries one risk that has to be handled rather than hoped away. The
encoder is multilingual, but its Turkish is almost certainly weaker than its
English. If Turkish shows no gain, two explanations survive: the account is
wrong, or the encoder is poor in Turkish. Nothing in a Turkish-only design
separates them.

MASSIVE separates them for free, because its locales are human-localised
parallel data rather than translations: the same content, in both languages,
with no translator in between — which is already an improvement on
`run_language_match.py`, whose German–English cross had to go through Marian and
therefore carried a translation-quality variable. Run both locales and encoder
quality stops being a confound and becomes a measurement: the terse baseline may
sit lower in Turkish, but the account predicts the *gain*, not the absolute
accuracy, and the gain is what has to behave the same in both.

English is therefore used in one place only — the language × description cross
of P5 — and not across the whole battery. That is a deliberate limit, not an
oversight: the paper already corrects one family of 72 comparisons, and doubling
this study's family to buy a control it only needs once would bury its own
results under the correction.

TTC-4900 has no parallel English and stays Turkish-only; its job is the
readable-names contrast, not the language cross.

## The class texts

Four arms, so that language and authorship are not confounded with each other:

1. **identifier** — the class name as the dataset ships it, in English.
2. **terse Turkish** — the same name in Turkish, nothing added.
3. **definition, assistant** — a Turkish definition written by the same
   assistant pipeline used for the main study, for comparability with
   `run_description_source.py`.
4. **definition, native speaker** — a Turkish definition written by the author,
   who is a native speaker.

Arm 4 is new to this project. `run_description_source.py` compares a terse
control, the assistant and an independent 7B model; none of those is a human
writing in their own language. It is an addition to that comparison, not a
replacement for any arm of it, and it must be written **before** any accuracy is
computed, from the class name alone, without looking at a single document or
error. Otherwise it is tuning, and it would quietly become the best arm for a
reason that has nothing to do with the account.

## Order of operations

Alignment uses the gold labels — it is the cosine between a class vector and
the centroid of that class's own documents — but it uses no accuracy. That is
the line this project's preregistrations actually draw, and the order
`results/brown_preregistration.json` followed: the alignment changes are
measured and committed, the predictions are derived from them, and only then is
a single document classified. (The label-*free* quantity is `pseudo_alignment`,
a different measurement belonging to the estimate of Section A1; it is not what
registers a prediction here.)

1. Fetch the corpora. Pin the new dependency in `requirements.txt`.
2. Write the four sets of class texts. Freeze them.
3. Compute the alignment change per class for each arm. No accuracy is computed.
4. Write the predictions below into `results/turkish_preregistration.json`,
   with the code revision and method fingerprint, and commit that file.
5. Only then compute accuracy, McNemar, bootstrap intervals and Holm correction
   over the new family.

If step 4 is not committed before step 5 runs, the study is an exploration and
has to be reported as one.

## The predictions

Written from the account, not from a guess, and to be registered verbatim:

- **P1.** On MASSIVE, replacing the identifier with a Turkish definition raises
  Top-1 accuracy.
- **P2.** On TTC-4900, replacing the readable category name with a definition
  does not raise Top-1 accuracy.
- **P3.** The ordering of the two gains follows the ordering of their mean
  alignment changes.
- **P4.** Within each corpus, the per-class alignment change correlates
  positively with the share of available headroom captured.
- **P5.** On MASSIVE, Turkish class texts beat English ones on Turkish
  documents, at both the intent and the scenario level.
- **P6.** The native-speaker definitions and the assistant's definitions differ
  by less than the gap between either of them and the terse control.

P6 is the one most likely to fail, and it is registered because of that. If a
native speaker writes a much better class text than the assistant does, the
paper's main effect is partly an artefact of who was available to write, and
that is worth knowing.

## What would falsify the account here

A positive alignment change with no gain on MASSIVE, or a gain on TTC-4900 as
large as MASSIVE's. Either outcome is reported with the same prominence as a
confirmation, in the same place as the seven registered predictions that already
failed.
