FROM python:3.13-slim

# libmagic1: required by python-magic for MIME sniffing (blueprint section 8.2).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copied whole (not just pyproject.toml) because the hatchling editable
# install needs the `app` package present to resolve at install time; the
# bind-mounted volume in docker-compose.yml keeps local edits live anyway.
#
# This install pulls in sentence-transformers (-> PyTorch CPU) for local
# BGE-M3 embeddings (blueprint section 9.4) — expect this layer to take
# several minutes and a few GB on first build. The model weights
# themselves (~2GB) are downloaded separately, at first ingestion, not
# at build time; see docs/runbooks/windows-local.md.
COPY apps/api/ ./
RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
