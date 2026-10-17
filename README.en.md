# DocDiffGuard

[中文](README.md) | English

A tool for comparing two documents and governing role confusion between them.

Given two documents, **BASE** (the polished, read-only reference) and **REF** (the transcribed version, which must not contain invented content), it finds content that is in BASE but missing from REF or semantically different, and summarizes it as a list of "points the transcription needs to change". Every conclusion can be traced back to the original text.

## Design principles

- **Explicit role binding**: roles are set with `--base` and `--ref`, not guessed from argument order.
- **One task, two files**: no history files are introduced, to avoid contamination.
- **Parse, segment and align first, then judge**: judgment only runs on the alignment results.
- **Rules first, LLM optional**: every conclusion is first produced by rules. The LLM only adds judgment on `fuzzy` candidates; without an API or when a call fails, it falls back to rule-based judgment.
- **Quotes must be verifiable**: every quoted source passage must be found in the corresponding document; passages that cannot be found are discarded and logged.

## Quick start

Requirements: Python 3.11+, preferably using the project's virtual environment `.venv`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Command line:

```bash
python aligner.py --base samples/base_test.docx --ref samples/ref_test.txt > result.json
python report.py result.json > report.md
```

LLM judgment (optional; requires the environment variable `ANTHROPIC_API_KEY`; without it, the tool falls back to rules):

```bash
python judge.py --base samples/base_test.docx --ref samples/ref_test.txt
```

Web interface:

```bash
streamlit run app.py
```

Evaluation:

```bash
python eval.py
python eval_llm.py
```

## Pipeline

| Step | File | What it does |
|---|---|---|
| 1. Read | `reader.py` | Reads `.txt` or `.docx`, splits into paragraphs, numbers them P001, R001 |
| 2. Bind | `binder.py` | Checks that both files exist, are not the same file, and are not empty; returns a `DocPair` |
| 3. Align | `aligner.py` | Computes similarity with `difflib`; for each BASE paragraph, takes the best match |
| 4. Classify | `aligner.py` | See "Classification rules" below |
| 5. Structure | `models.py` | Defines `AlignmentResult` with Pydantic, validating field types and value ranges |
| 6. Validate | `aligner.py` | `validate_results`: quotes must be found in the source text, otherwise discarded |
| 7. Report | `report.py` | Groups by `missing` and `modified`, produces the change list |
| 8. Judge (optional) | `judge.py` | Calls the LLM only on `fuzzy` candidates, outputs JSON and checks the evidence; falls back to rule-based judgment if the API fails or the output cannot be parsed |

## Classification rules

1. Before computing similarity, remove punctuation and whitespace.
2. Similarity thresholds:
   - Above 0.92 and with no substantive insertions or deletions: `same`;
   - 0.75 to 0.92: `fuzzy` (called "modified" in the report; needs manual review);
   - Below 0.75: `missing` (no corresponding content in REF).
3. Any substantive insertion or deletion of text prevents `same`, even if the score is above 0.92.
4. `fuzzy` candidates may be passed to the LLM. The LLM output must match the `JudgeVerdict` structure, and its `evidence` must be found in the BASE text.

The thresholds 0.92 and 0.75 were set by hand and have not been calibrated against real document data.

## Evaluation

Evaluation cases are in `eval_cases.json`: 20 cases in total, covering:
- the three labels (`same`, `fuzzy`, `missing`);
- punctuation differences, deletions, and number changes;
- multiple paragraphs, swapped paragraph order, REF with extra content, and REF missing content.

Rule-based metrics (on these 20 self-built cases):

| Metric | Result |
|---|---|
| Difference detection: precision / recall / F1 | 1.000 / 1.000 / 1.000 |
| Order accuracy (17 checks) | 1.000 |
| Citation accuracy / hallucination rate | 1.000 / 0.000 |
| Format compliance rate | 1.000 |
| Role confusion rate | 0.000 |

**Note**: perfect scores only show that the rules are correct on the self-built cases, not that they are accurate on real documents. Citation accuracy, hallucination rate, format compliance and role confusion cannot go wrong in the rule-only pipeline; they are guard metrics, mainly for catching problems introduced by LLM judgment.

LLM judgment evaluation (`python eval_llm.py`, 17 paragraphs, about 17 API calls):
- `fuzzy`: 4 cases, 4 match expectations, 0 fallbacks;
- `same`: 13 cases, 13 match expectations, 0 fallbacks.

These are results on self-built cases with a very small sample; they do not represent accuracy on real documents. When counting, results that fell back are not counted as correct LLM results.

### Real-document check (one document pair, limited results)

This is the only check this project has run on real documents, and it was run only once. It uses two versions of a personal document: B1 (BASE, polished, 57 paragraphs) and B2 (REF, transcribed, 56 paragraphs).

**Something went wrong during the check**: while B2 was being transcribed, Kimi (an AI tool) added unauthorized content and used data from B0 (the original version). I had not asked it to do this. That content was, for a time, treated as part of the verification results. The numbers below therefore only describe how the tool reacts to this B2, not its accuracy on a clean document. To guard against this, the project added `check_additions.py`, which checks whether a target document contains sentences that are not found in its allowed sources.

**The original documents for this check are not published.**

- **Rule-based pipeline**: 52 `same`, 4 `fuzzy`, 1 `missing`.
- **Labels**: draft labels were written by the author after reading the full text; they have not been checked by a second person. Using them, at the default thresholds (0.92 / 0.75), precision is 0.80, recall is 1.00, and F1 is 0.889; the three labels match in 55 of 57 paragraphs. Results do not change across 0.85–0.95 and 0.70–0.80.
- **Known errors**:
  - P030: the background paragraph was rewritten and expanded; the rules label it `missing`, but it should be `fuzzy`.
  - P031: its content is fully contained in a merged paragraph in B2; the rules label it `fuzzy`, but it should be `same`. Both cases come from paragraph segmentation differences, which one-to-one best matching cannot handle.
- **LLM judgment**: four `fuzzy` paragraphs were sent to the LLM; all calls succeeded (0 fallbacks). In 3 of them, the `evidence` could not be found verbatim in BASE, so the evidence check discarded it. P031 was labeled `modified`, which disagrees with the draft label, for the same segmentation reason.
- **Source check** (`check_additions.py`): 5 sentences in B2 come from B0 and are not in B1; another sentence is in neither B0 nor B1 and needs manual review.

## Failure modes and known limitations

- **Small deletions judged as unchanged**: deleting 5 characters still left the score above 0.92. Fixed: substantive insertions or deletions no longer count as `same`. Found by case C005.
- **Punctuation differences lower scores of short sentences**: for example, "报告！" and "报告。" differ by one character, but short sentences fall below 0.92 and are mislabeled `fuzzy`. Fixed: punctuation is removed before comparison. Found by case C008.
- **Character-based, no semantic understanding**: paraphrases may be labeled `missing` or `fuzzy`.
- **Best matches may repeat**: two BASE paragraphs may point to the same REF paragraph. For example, P002 and P003 are themselves very similar, and in a fully copied REF, P003 scores 0.903 against R002.
- **Guard metrics have no real detection power**: in the rule-only pipeline these metrics are always 100%.
- **LLM output may be truncated**: the model's reasoning uses up `max_tokens`, and the visible text may be empty or incomplete when the budget runs out. Fixed by raising `max_tokens` to 4096; changing models or documents may require adjusting it again.
- **LLM output format is unstable**: the model sometimes wraps JSON in a code block. Fixed by extracting only the text from the first `{` to the last `}`.
- **Temporary files are not cleaned up**: the web interface creates a new file in the system temp directory on every refresh.
- **Limited format support**: only `.txt` and `.docx`; `.pdf` is not supported.

## Retrospective

- **Verify every step with real output**, not just by reading the code. Several times, things looked right but had not actually run: the command ran in the wrong terminal window, a file was not saved, or a file was in the wrong place.
- **Test-driven rule fixes**: the failures of C005 and C008 directly led to rule changes. The fixes improved the rules and did not change the expected values.
- **Exclude fallback results from statistics**: after an LLM call fails and falls back to rules, the result may happen to match the expectation; counting it as an LLM success would overstate the LLM's performance. This was found during evaluation.
- **Passing everything is not the same as being accurate**: the 20 self-built cases were designed by us and adjusted step by step after failures, so they may be biased. Real-document testing is the next step.
- **Validate before connecting**: build the interface with the key-free fallback first, then connect the real calls, confirming each step with real output.

## Roadmap

- Done: the main content of stages 0 to 10, including rule-based alignment, structured output, evaluation, the Streamlit interface, and optional LLM judgment (stage 7).
- To do: clean up temporary files; redo the real-document check with a clean B2 and manually confirmed labels; add real-document paragraphs to the evaluation cases; support `.pdf` (not planned for now).

## Directory layout

```
docdiffguard/
├── reader.py            Reads .txt / .docx and splits into paragraphs
├── binder.py            Binds BASE and REF and checks inputs
├── aligner.py           Similarity, classification, result building and validation
├── models.py            Pydantic structured results (AlignmentResult, JudgeVerdict)
├── report.py            Produces the change list
├── check_additions.py   Lists sentences in the target document that are not found in any source
├── judge.py             LLM judgment (with rule fallback) and evidence checks
├── eval.py              Evaluation script
├── eval_llm.py          Evaluation script for LLM judgment
├── eval_cases.json      20 self-built evaluation cases
├── app.py               Streamlit interface
├── requirements.txt     Dependencies
└── samples/             Test BASE and REF files
```
