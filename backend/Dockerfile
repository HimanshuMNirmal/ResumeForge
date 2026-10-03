# ── Stage 1: deps ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /build

# System deps for pdfplumber, python-docx, cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install core engine in editable mode
COPY src/ ./src/
RUN pip install --no-cache-dir -e ./src[all]

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# LibreOffice for DOCX→PDF conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy source
COPY --from=deps /build/src ./src
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
