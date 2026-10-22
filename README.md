# Multi-Agentic Cybersecurity

# This project is just a framework - final work could be different but will be using this repository for future development

This project is a Google ADK multi-agent retrieval system that:

- ingests local documents into Qdrant
- chunks content with hybrid chunking (structure-aware + semantic boundaries)
- embeds chunks with the configured embedding provider (Ollama by default)
- retrieves relevant context for grounded answers
- prepares Confluence publish payloads
- publishes directly to Confluence through its REST API

## Prerequisites

- Python 3.13 (matches the `Dockerfile` and `pyproject.toml`)
- Ollama, with `qwen2.5:7b` and `nomic-embed-text` pulled (the default LLM and embedding providers)
- Docker Desktop (for the local Qdrant container)
- Node.js and npm (for the browser extension)
- Optional: a Google API key (`GOOGLE_API_KEY`) if you use Gemini
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

Then run the keyword-recall baseline, which does not need the LLM judge:

```powershell
.\.venv\Scripts\python -m agents.eval.ragas --keyword-only
```

This writes a report to `.artifacts/retrieval-report.json`. Without `--keyword-only`, the command runs the RAGAS judge metrics against the local Ollama models and writes `.artifacts/ragas-report.json`.

## 6. Start the backend API server

The browser extension calls the ADK API server, so start this command (not `adk web`):

```powershell
.\.venv\Scripts\adk.exe api_server agents --port 8000 --host 127.0.0.1 --allow_origins 'regex:chrome-extension://(gjicmadlhaabnjngkinahbedaghaiblf|mhpjopnhfojchhjimknnpoafcgmgjpak)'
```

The server listens on `http://127.0.0.1:8000`. The `--allow_origins` regex lists the extension IDs allowed to call it; update it if your unpacked extension has a different ID.

### PDF and image attachments

Attachment analysis extracts text from PDFs and uses local Tesseract OCR for
screenshots and scanned PDF pages. Install Tesseract OCR and ensure `tesseract`
is available on `PATH`; set `TESSERACT_CMD` if its executable is elsewhere.
Uploads are limited to 20 MB and PDF processing to the first 20 pages.

### Browser extension

The extension in `extension/` is a WXT and React side panel. It needs the backend from section 6 running on `http://127.0.0.1:8000`. Setup, run, and build steps are in [extension/README.md](extension/README.md).

### Agent integrity manifest

`agents/agent_manifest.json` stores a fingerprint of every agent's description and instruction. At startup, `agents/agent.py` compares the live agents with the manifest and refuses to start if they differ.

After any change to a `prompt.md` file or an agent description, run:

```powershell
.\.venv\Scripts\python -m agents.integrity
```

Then commit the updated `agents/agent_manifest.json` with the change. Setting `AGENT_MANIFEST_UPDATE=1` skips the check. Only the update command should set it; never set it in production.

### Docker

The `Dockerfile` builds the backend API server image on Python 3.13. `.dockerignore` excludes `.env`, so secrets are not copied into the image.

If you changed any prompt or agent description, run the integrity command above before building, because the image includes `agents/agent_manifest.json`.

```powershell
docker build -t multi-agentic-cybersecurity .
docker run -p 8000:8000 --env-file .env multi-agentic-cybersecurity
```

- Inside the container, `localhost` refers to the container itself. Point `QDRANT_URL` and `OLLAMA_BASE_URL` at a reachable address, for example `http://host.docker.internal:6333` and `http://host.docker.internal:11434` on Docker Desktop, or use a remote Qdrant URL.
- The container runs as a non-root user. `agents/` is read-only; only `data/` is writable.
- The default start command does not include the `--allow_origins` option used for local extension runs.
- On Render, set the same variables in the service environment instead of using `--env-file`. Render injects `PORT`.

## 7. Optional: publish to Confluence

Publishing uses the Confluence REST API with `CONFLUENCE_BASE_URL`, `CONFLUENCE_EMAIL`, and `CONFLUENCE_API_TOKEN`.

The direct publish helpers default to a `dry_run` preview, so you can validate the generated payload before writing to Confluence.

## 8. Environment variables

The project expects the following variables in `.env`:

```dotenv
GOOGLE_GENAI_USE_ENTERPRISE=0
GOOGLE_API_KEY=your_google_api_key_here
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
OPENROUTER_API_KEY=
OPENROUTER_MODEL=nvidia/nemotron-3.5-lightning:free

EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text:latest
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
By default, agent responses and knowledge embeddings use local Ollama models.
All teammates must use the same embedding model for ingestion and retrieval
against the shared Qdrant collection.

To use OpenRouter for agent responses, set `LLM_PROVIDER=openrouter` and put your
key in `OPENROUTER_API_KEY` in the local `.env` file. The default model above is
the free Nemotron variant. Keep the key private; do not put it in `.env.example`
or commit `.env`. Embeddings continue to use the configured `EMBEDDING_PROVIDER`.

## 9. Common troubleshooting

### `Missing required environment variable`

Make sure you copied `.env.example` to `.env` and filled in the real values.

### `Connection refused` to Qdrant

Check that Docker Desktop is running and that the Qdrant container is started on port `6333`.

### Embedding errors

Verify that Ollama is running, `EMBEDDING_MODEL` is installed, and its vector
dimension matches `EMBEDDING_DIM`.

### `adk api_server` fails to start

Make sure the virtual environment is active and dependencies were installed from `requirements.txt`.

### `Agent definitions changed without updating the manifest`

A prompt or agent description changed. Run `.\.venv\Scripts\python -m agents.integrity`, then restart the server.

## Lint, type checks, and baseline

Install the pinned dev tools (ruff and pyright) into the same virtual environment:

```powershell
.\.venv\Scripts\pip install -r requirements-dev.txt
```

From the project root, run:

```powershell
.\.venv\Scripts\python scripts\lint_baseline.py
```

This compares ruff and pyright findings with `lint-baseline.json` and fails only on new findings. Run it with `--update` to accept the current findings as the new baseline. Pyright needs Node.js.

## Main workflow summary

1. create `.env` from `.env.example`
2. start Qdrant
3. run `python -m agents.eval.smoke`
4. run `python -m agents.eval.ingest agents/tools/knowledge/data.md`
5. run `python -m agents.eval.ragas --keyword-only`
6. start the backend with `adk.exe api_server` (section 6)

This is the recommended local setup for running the project on a fresh machine.
