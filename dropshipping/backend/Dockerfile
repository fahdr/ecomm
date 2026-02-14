# Multi-stage Dockerfile for the Dropshipping Backend API.
#
# Stage 1: Install Python dependencies in a venv.
# Stage 2: Copy the venv and app code into a slim runtime image.
#
# **For Developers:**
#   Build: docker build -t dropshipping/backend .
#   Run:   docker run -p 8000:8000 --env-file .env dropshipping/backend
#
# **For QA Engineers:**
#   The health endpoint at /api/v1/health confirms the container is running.

FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

COPY . .
RUN pip install --no-cache-dir .

# ── Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
