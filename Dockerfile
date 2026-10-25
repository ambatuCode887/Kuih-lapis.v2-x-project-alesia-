FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Agent code is read-only for the app user; only data/ (the unanswered-question log) is writable.
RUN useradd --system --uid 10001 --no-create-home appuser \
    && chmod -R a-w agents \
    && mkdir -p data \
    && chown appuser data
USER appuser

# Render injects PORT; secrets come from Render environment variables, not from a copied .env.
CMD ["sh", "-c", "adk api_server agents --host 0.0.0.0 --port ${PORT:-8000} --allow_origins 'regex:chrome-extension://(gjicmadlhaabnjngkinahbedaghaiblf|mhpjopnhfojchhjimknnpoafcgmgjpak)'"]