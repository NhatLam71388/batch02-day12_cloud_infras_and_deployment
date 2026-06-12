# ============================================================
# Production Dockerfile — Multi-stage, non-root user
# Build context = 06-lab-complete/ (chạy: docker compose up)
# ============================================================

# Stage 1: Builder — cài packages
FROM python:3.11-slim AS builder

WORKDIR /build

# gcc cần cho một số C-extension packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user --timeout 120 --retries 10 -r requirements.txt


# Stage 2: Runtime — image nhỏ, không có build tools
FROM python:3.11-slim AS runtime

# Non-root user (best practice)
RUN groupadd -r agent && useradd -r -g agent -d /app -s /sbin/nologin agent

WORKDIR /app

# Copy chỉ packages đã cài từ builder (không copy gcc, apt cache)
COPY --from=builder /root/.local /home/agent/.local

# Copy application code
COPY app/ ./app/

RUN chown -R agent:agent /app

USER agent

ENV PATH=/home/agent/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check built into image
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
