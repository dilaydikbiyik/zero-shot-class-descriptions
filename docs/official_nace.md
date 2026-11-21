# The official NACE notes as an externally authored control

This is the written half of the study registered in
`results/official_nace_preregistration.json`. It exists because a reader is
entitled to know what the study was for before seeing what it found, and
because the design has one awkward property that is better stated here than
discovered in review.

## The objection it answers

`run_description_source.py` answers "was it this writer?" — it replaces the
assistant's definitions with an independent 7B model's and part of the effect
survives. It cannot answer "was it this project?" Every arm of that comparison
was written for this study, from this taxonomy, by a writer who had been shown
the material. A reviewer can say, correctly, that the descriptions carrying the
main effect were produced by the same people who then measured them, and no arm
of any existing study separates that.

The control that separates it has to be text nobody here chose. For arXiv the
paper already has one, because arXiv's category descriptions are arXiv's own —
but arXiv is not where any headline figure comes from. NACE is, and NACE has an
official class text: the explanatory notes of WZ 2008, the German
implementation of NACE Rev. 2, published by the Statistisches Bundesamt in
2008. They are in German, the language of the documents. They were written
years before this project, by people who had never seen it, for the use of the
registrars whose filings make up the corpus.

## The four arms

| arm | description text | words per class |
| --- | --- | --- |
| terse German name | the section's short name, hand-translated | 10 |
| definitions by the assistant | the paper's own descriptions | 19 |
| the official note, verbatim | the WZ 2008 note | 147 |
| the official note, first sentence | its first sentence only | 26 |

The first two are the control and the treatment of the description study and of
the description-source study, re-run here, so the three studies share a
baseline and the numbers in this one can be read against the others.

Every arm carries the control's section name and varies only the description
after it. That is the construction `run_description_source.py` uses; keeping it
means the arms differ in their descriptions and in nothing else.

## Why the official text enters twice

Because one external arm would confound the question with its answer. The
official note is both externally authored *and* far longer — 147 words per
class against this project's 19, and 670 for section C alone. A gain from that
arm could be read either way, and whichever reading suited the paper would be
the one available.

The first-sentence arm fixes the length and not the authorship: 26 words per
class, within seven of the assistant's own arm. It does not close the gap
perfectly — six sections keep a first sentence longer than this project's
longest description, L worst at 48 words — but it moves the comparison from
nearly sixfold to near-parity, and the registration records the mean words per
class for all four arms so a length reading stays checkable.

What the pair buys is the comparison between them. A length explanation of any
external gain has to predict that the two arms, differing by a factor of six in
length and not at all in authorship, behave differently. An authorship
explanation has to predict they behave alike.

## What the registration actually predicts, and why that is uncomfortable

The predictions are not authored. `predictions_from` reads each direction off a
measured alignment change, so there is no step at which a direction could be
chosen to match an accuracy. What the alignment came out as is this:

| arm | mean alignment change vs. control |
| --- | --- |
| definitions by the assistant | **+0.080** |
| the official note, verbatim | **+0.021** |
| the official note, first sentence | **−0.005** |

So the registered prediction is that the verbatim note *raises* accuracy and
its first sentence *lowers* it — that the two official arms diverge. That is
the length pattern, not the authorship pattern. The study therefore goes in
predicting, in advance and on the record, the outcome least flattering to the
reading the control was built to support: that what the long official note buys
is partly length rather than an outside author.

This is worth being plain about. If the prediction holds, the paper does not
get to say "the effect appears with class texts nobody here wrote" without
qualification; it gets to say that a long external text helps, that a
length-matched external text does not, and that the project's own descriptions
beat both at a fifth of the length. That is a weaker claim about authorship and
a sharper one about what a class text has to do. It is also the claim the data
supports, which is the only reason to make either.

If the prediction fails — if the first sentence gains too — the authorship
reading comes out stronger than this registration expected, and that will have
been predicted against rather than fitted.

## The label space, and what it costs

Sections T and U carry no explanatory note. They are recorded as missing in
`sectors_official.json` rather than filled from their titles, because a
substituted title would make the official arms partly terse arms and flatter
whichever comparison they lost.

They are then dropped from the label space of **all four** arms. An argmax over
19 classes is an easier problem than one over 21, so letting the arms that
*can* describe T and U keep them would hand the official arms a smaller
haystack than the others, and the comparison would stop being about class text.

No evaluation document is lost: the 299 labelled documents cover 18 sections
and neither T nor U is among them. What is lost is comparability — every
accuracy in this study is 19-way and must not be set beside the paper's 21-way
figures. The control is re-run inside the study for exactly this reason, so
every number here has a baseline measured on the same problem.

## What would falsify the account here

An arm that raises alignment and does not raise accuracy. The alignment account
claims a class text works by sitting nearer the documents it must attract; an
arm that moves the first quantity and not the second is the account failing on
its own terms, and `outcomes` in `results/official_nace.json` records it as a
failure rather than as a null.

The per-class test is the same claim at finer grain: for the verbatim note, the
per-class alignment change should correlate positively with the share of
available headroom captured. With 18 classes it is a weak test, and it is
reported with its n.
