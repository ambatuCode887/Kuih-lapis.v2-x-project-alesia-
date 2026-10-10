# Multi-Agentic Cybersecurity

# This project is just a framework - final work could be different but will be using this repository for future development

This project is a Google ADK multi-agent retrieval system that:

- ingests local documents into Qdrant
- chunks content with hybrid chunking (structure-aware + semantic boundaries)
- embeds chunks with Google Gemini embeddings
- retrieves relevant context for grounded answers
- prepares Confluence publish payloads
- publishes directly to Confluence through its REST API

## Prerequisites

- Python 3.10+
- Docker Desktop (for the local Qdrant container)
- A Google API key for Gemini embeddings
- Optional: Confluence credentials if you want direct publishing

## 1. Create your local environment

From the project root, create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\pip install -r requirements.txt
```

Then create your local environment file from the example template:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace the placeholders with your own values.

> Important: do not commit the real `.env` file. Keep secrets in your local machine only.

The project already supports loading environment variables from either the workspace root `.env` or `agents/.env`.

## 2. Start Qdrant locally

If you are using the local Docker-based setup, start Qdrant like this:

```powershell
docker run -p 6333:6333 -v ${PWD}\.qdrant:/qdrant/storage qdrant/qdrant
```

You can also point `QDRANT_URL` at a remote Qdrant instance if you prefer.

Check that the local endpoint is reachable:

```powershell
Test-NetConnection localhost -Port 6333
```

## 3. Run a smoke check

```powershell
.\.venv\Scripts\python -m agents.eval.smoke
```

This command validates that the chunking path and publish payload preparation work with the current configuration.

## 4. Ingest knowledge documents

The project includes a sample knowledge file and evaluation dataset:

- `agents/tools/knowledge/data.md`
- `agents/tools/knowledge/dataset.csv`

Run ingestion like this:

```powershell
.\.venv\Scripts\python -m agents.eval.ingest agents/tools/knowledge/data.md
```

Optional: disable semantic chunking and use the fallback fixed-size chunker:

```powershell
.\.venv\Scripts\python -m agents.eval.ingest agents/tools/knowledge/data.md --no-semantic
```

## 5. Run retrieval evaluation

First make sure your evaluation dataset has cases in `agents/tools/knowledge/dataset.csv`.

Then run:

```powershell
.\.venv\Scripts\python -m agents.eval.ragas
```

This writes a report to `.artifacts/retrieval-report.json`.

## 6. Start the ADK web app

```powershell
.\.venv\Scripts\adk web
```

Then open the local URL shown in the terminal (typically `http://127.0.0.1:8000`).

## 7. Optional: publish to Confluence

Publishing uses the Confluence REST API with `CONFLUENCE_BASE_URL`, `CONFLUENCE_EMAIL`, and `CONFLUENCE_API_TOKEN`.

The direct publish helpers default to a `dry_run` preview, so you can validate the generated payload before writing to Confluence.

## 8. Environment variables

The project expects the following variables in `.env`:

```dotenv
GOOGLE_GENAI_USE_ENTERPRISE=0
GOOGLE_API_KEY=your_google_api_key_here

EMBEDDING_PROVIDER=google
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIM=768

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=multi_agentic_rag

CONFLUENCE_BASE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_EMAIL=you@example.com
CONFLUENCE_API_TOKEN=your_confluence_api_token_here
CONFLUENCE_SPACE_KEY=YOUR_SPACE_KEY
CONFLUENCE_PARENT_ID=
```

A reusable skeleton is already provided in `.env.example`.

## 9. Common troubleshooting

### `Missing required environment variable`

Make sure you copied `.env.example` to `.env` and filled in the real values.

### `Connection refused` to Qdrant

Check that Docker Desktop is running and that the Qdrant container is started on port `6333`.

### Embedding API errors

Verify that `GOOGLE_API_KEY` is valid and that `EMBEDDING_MODEL` matches a supported model.

### `adk web` fails to start

Make sure the virtual environment is active and dependencies were installed from `requirements.txt`.

## Main workflow summary

1. create `.env` from `.env.example`
2. start Qdrant
3. run `python -m agents.eval.smoke`
4. run `python -m agents.eval.ingest agents/tools/knowledge/data.md`
5. run `python -m agents.eval.ragas`
6. start `adk web`

This is the recommended local setup for running the project on a fresh machine.
