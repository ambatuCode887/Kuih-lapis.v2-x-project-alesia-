FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Agent code is read-only for the app user; only data/ (the unanswered-question log) is writable.
RUN if [ -z "$(getent group 1000)" ]; then groupadd --gid 1000 rendersecrets; fi \
    && useradd --system --uid 10001 --no-create-home appuser \
    && usermod --append --groups 1000 appuser \
    && chmod -R a-w agents \
    && mkdir -p data \
    && chown appuser data
USER appuser

# Render injects PORT; secrets come from Render environment variables, not from a copied .env.
CMD ["sh", "-c", "adk api_server agents --host 0.0.0.0 --port ${PORT:-8000} --allow_origins 'regex:chrome-extension://(gjicmadlhaabnjngkinahbedaghaiblf|mhpjopnhfojchhjimknnpoafcgmgjpak|nbdnadfijjopoknmfjkbcbpkgfgmkikh)'"]