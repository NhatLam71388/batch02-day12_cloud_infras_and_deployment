"""
Agent Render-ready.
Render inject PORT env var tự động — agent phải dùng os.getenv("PORT").
"""
import os
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from utils.mock_llm import ask

app = FastAPI(title="Agent on Render", version="1.0.0")
START_TIME = time.time()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "AI Agent running on Render!",
        "docs": "/docs",
        "health": "/health",
    }


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
async def ask_agent(req: AskRequest):
    # Pydantic model → Swagger UI tự sinh ô nhập body + validate
    if not req.question.strip():
        raise HTTPException(422, "question required")
    return {
        "question": req.question,
        "answer": ask(req.question),
        "platform": "Render",
    }


@app.get("/health")
def health():
    """
    Render sẽ check endpoint này định kỳ.
    Trả về 200 = healthy. Non-200 = Render restart container.
    """
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "platform": "Render",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    # ✅ Render inject PORT — PHẢI đọc từ env
    port = int(os.getenv("PORT", 8000))
    print(f"Starting on port {port} (from PORT env var)")
    uvicorn.run(app, host="0.0.0.0", port=port)
