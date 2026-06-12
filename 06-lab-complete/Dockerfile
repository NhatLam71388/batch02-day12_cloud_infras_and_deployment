# ============================================================
# Multi-stage production Dockerfile
# Stage 1: install deps → Stage 2: minimal runtime, non-root
# ============================================================

# ── Stage 1: builder ────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --prefix=/packages installs to /packages/lib/python3.11/site-packages/
RUN pip install --no-cache-dir --prefix=/packages --timeout 120 --retries 10 -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

# -m creates /home/agent automatically; no interactive shell
RUN groupadd -r agent && useradd -r -g agent -m -s /sbin/nologin agent

WORKDIR /app

# Copy packages to system path — always found regardless of HOME
COPY --from=builder /packages /usr/local/

COPY start.py .
COPY app/ ./app/

RUN chown -R agent:agent /app

USER agent

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "start.py"]
