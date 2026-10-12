# Retrieval evaluation

## RAGAS evaluation

The default command evaluates generated answers against reference answers. It retrieves context from Qdrant, generates answers with the configured local Ollama model, and reports RAGAS faithfulness, answer relevancy, context recall, context precision, and factual correctness.

Run a repeatable 10-row sample from the newly ingested Q&A CSV:

```powershell
.\.venv\Scripts\python -m agents.eval.ragas
```

Evaluate every row (this may take a long time with a local judge model):

```powershell
.\.venv\Scripts\python -m agents.eval.ragas --limit 0
```

The report is written to `.artifacts/ragas-report.json`. The default questions come from the indexed knowledge CSV, so this is an in-sample check. For a held-out evaluation, pass a separate CSV with `question` and `answer` columns using `--dataset`.

## Keyword-recall baseline

Add one row per evaluation question to `agents/tools/knowledge/dataset.csv`:

```csv
id,question,reference_answer,expected_keywords
case-1,What is credential stuffing?,An attack using leaked passwords.,credential stuffing|leaked passwords
```

Ingest the knowledge documents first:

```powershell
.\.venv\Scripts\python -m agents.eval.ingest agents/tools/knowledge/data.md
```

Run the lightweight expected-keyword recall baseline:

```powershell
.\.venv\Scripts\python -m agents.eval.ragas --keyword-only
```

The report is written to `.artifacts/retrieval-report.json`. This baseline measures expected-keyword recall in retrieved context and does not grant or deny Confluence publication permission.

## Held-out retrieval and grounding check

The held-out questions are separately worded from the indexed Q&A corpus and the
development questions. Their reference answers and expected keywords are based
on `agents/tools/knowledge/data.md`. Keep this file unchanged while tuning; use
`retrieval_dev_cybersecurity.csv` for iteration. The keyword score is literal
substring recall over the retrieved top five chunks, not a semantic relevance
judgment.

Run retrieval recall over all held-out cases:

```powershell
.\.venv\Scripts\python -m agents.eval.ragas --keyword-only --dataset agents/eval/heldout_cybersecurity.csv --output .artifacts/heldout-retrieval.json
```

Run a repeatable four-case source-citation audit. It checks whether answer
citations refer to retrieved chunks without invoking the stalled local RAGAS
judge. This is a citation audit, not a semantic faithfulness score:

```powershell
.\.venv\Scripts\python -m agents.eval.ragas --grounding-only --dataset agents/eval/heldout_cybersecurity.csv --limit 4 --seed 42 --output .artifacts/heldout-ragas.json
```

Citation validity only checks whether answer citations identify retrieved
source/chunks. A valid citation alone does not prove that the cited passage
supports every claim. The normal RAGAS faithfulness metric remains available
without `--grounding-only` when the local judge responds reliably.

## Scam-assessment evaluation

Review the expected labels and notes in `agents/eval/scam_assessment_cases.csv`
before running the model evaluation. The runner refuses cases that are not
marked `reviewed`.

Run one case as a quick model/runner smoke check:

```powershell
.\.venv\Scripts\python -m agents.eval.scam_assessment --limit 1
```

Run all reviewed cases:

```powershell
.\.venv\Scripts\python -m agents.eval.scam_assessment
```

The JSON report is written to `.artifacts/scam-assessment-report.json` by
default. It records schema validity, exact risk-level agreement, expected
indicator recall, and agreement with the coordinator's clarification route.
These are comparisons against reviewed heuristic labels, not calibrated
probabilities or proof that a message is fraudulent. Manually inspect the
per-case responses, especially disagreements and safety-critical cases.
