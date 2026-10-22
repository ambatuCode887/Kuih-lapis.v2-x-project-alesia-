FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects PORT; secrets come from Render environment variables, not from a copied .env.
CMD ["sh", "-c", "adk api_server agents --host 0.0.0.0 --port ${PORT:-8000}"]
