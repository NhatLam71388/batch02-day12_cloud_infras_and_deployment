# Dockerfile cho stateless agent (Part 5)
# Build context = gốc repo (xem docker-compose.yml: context: ../..)
FROM python:3.11-slim

WORKDIR /app

COPY 05-scaling-reliability/production/requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt

COPY 05-scaling-reliability/production/app.py .
RUN mkdir -p utils
COPY utils/mock_llm.py utils/

EXPOSE 8000

CMD ["python", "app.py"]
