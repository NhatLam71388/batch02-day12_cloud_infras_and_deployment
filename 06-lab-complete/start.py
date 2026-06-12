"""Entrypoint — đọc PORT từ environment (Railway sets $PORT dynamically)."""
import os
import uvicorn

port = int(os.environ.get("PORT", 8000))
print(f"[start] Binding on port {port}")

uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=port,
    log_level="info",
)
