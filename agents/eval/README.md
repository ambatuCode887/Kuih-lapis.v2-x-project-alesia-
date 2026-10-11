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
