FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY data/raw/walk.graphml data/raw/walk.graphml
COPY data/processed/segment_features.parquet data/processed/segment_features.parquet

RUN useradd --create-home appuser
USER appuser

EXPOSE 8080
CMD ["sh", "-c", "python -m uvicorn src.web.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
