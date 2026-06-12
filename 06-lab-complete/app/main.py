"""
Production AI Agent — Day 12 Final Project
Tích hợp Day-3 ReAct E-commerce Agent với đầy đủ production features:

  ✅ Config từ environment (12-Factor)
  ✅ Structured JSON logging
  ✅ API Key authentication (X-API-Key header)
  ✅ Rate limiting — sliding window 10 req/min
  ✅ Cost guard — daily budget cap
  ✅ Input validation (Pydantic)
  ✅ Health check (/health) + Readiness probe (/ready)
  ✅ Graceful shutdown (lifespan + SIGTERM)
  ✅ Security headers
  ✅ CORS
  ✅ Web UI (Day-3 Jinja2 frontend)
  ✅ Real LLM: OpenAI / Gemini (fallback mock nếu không có key)
  ✅ ReAct agent với 3 tools: stock, discount, shipping
"""
import os
import time
import signal
import logging
import json
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
    force=True,
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# ─────────────────────────────────────────────────────────
# Rate Limiter — Sliding Window
# ─────────────────────────────────────────────────────────
_rate_windows: dict[str, deque] = defaultdict(deque)

def check_rate_limit(key: str):
    now = time.time()
    window = _rate_windows[key]
    while window and window[0] < now - 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min. Retry after 60s.",
            headers={"Retry-After": "60"},
        )
    window.append(now)

# ─────────────────────────────────────────────────────────
# Cost Guard
# ─────────────────────────────────────────────────────────
_daily_cost = 0.0
_cost_reset_day = time.strftime("%Y-%m-%d")

def check_and_record_cost(input_tokens: int, output_tokens: int):
    global _daily_cost, _cost_reset_day
    today = time.strftime("%Y-%m-%d")
    if today != _cost_reset_day:
        _daily_cost = 0.0
        _cost_reset_day = today
    if _daily_cost >= settings.daily_budget_usd:
        raise HTTPException(503, f"Daily budget ${settings.daily_budget_usd} exhausted.")
    # GPT-4o-mini pricing estimate
    cost = (input_tokens / 1_000_000) * 0.15 + (output_tokens / 1_000_000) * 0.60
    _daily_cost += cost

# ─────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key

# ─────────────────────────────────────────────────────────
# LLM Provider factory (Day-3 providers + mock fallback)
# ─────────────────────────────────────────────────────────
def get_llm_provider():
    """Trả về LLM provider theo config. Fallback mock nếu không có key."""
    provider = settings.default_provider.lower()
    model = settings.llm_model

    try:
        if provider == "openai" and settings.openai_api_key:
            from app.core.openai_provider import OpenAIProvider
            return OpenAIProvider(model_name=model, api_key=settings.openai_api_key)

        if provider in ("google", "gemini") and settings.gemini_api_key:
            from app.core.gemini_provider import GeminiProvider
            return GeminiProvider(model_name=model, api_key=settings.gemini_api_key)
    except Exception as e:
        logger.warning(json.dumps({"event": "provider_init_fail", "error": str(e)}))

    # Fallback: mock provider
    return None

# ─────────────────────────────────────────────────────────
# Lifespan (graceful startup + shutdown)
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    provider = get_llm_provider()
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "llm_provider": settings.default_provider if provider else "mock",
        "llm_model": settings.llm_model,
    }))
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield  # app chạy ở đây

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown", "total_requests": _request_count}))

# ─────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-ready E-commerce AI Agent (ReAct) — Day 12 Final Project",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Static files + Jinja2 templates (Day-3 web UI)
_app_dir = os.path.dirname(__file__)
_static_dir = os.path.join(_app_dir, "static")
_templates_dir = os.path.join(_app_dir, "templates")

if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")
templates = Jinja2Templates(directory=_templates_dir) if os.path.isdir(_templates_dir) else None

# ─────────────────────────────────────────────────────────
# Security + Logging Middleware
# ─────────────────────────────────────────────────────────
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    response: Response = await call_next(request)
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    if "server" in response.headers:
        del response.headers["server"]
    duration = round((time.time() - start) * 1000, 1)
    logger.info(json.dumps({
        "event": "request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": duration,
    }))
    return response

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Câu hỏi gửi tới agent")
    mode: str = Field("agent", description="'agent' (ReAct) hoặc 'chatbot' (baseline)")

class AskResponse(BaseModel):
    question: str
    answer: str
    mode: str
    model: str
    steps: list = []
    timestamp: str

# Day-3 original UI request model (giữ nguyên để UI hoạt động)
class ChatRequest(BaseModel):
    message: str
    provider: str
    model: str
    mode: str
    api_key: Optional[str] = None

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["UI"])
async def serve_ui(request: Request):
    """Phục vụ Day-3 web UI."""
    if templates:
        return templates.TemplateResponse(request, "index.html", {"request": request})
    return {"message": "Web UI not available", "api": "POST /ask with X-API-Key header"}


@app.post("/api/chat", tags=["UI"])
async def ui_chat(payload: ChatRequest, request: Request):
    """
    Endpoint cho Day-3 web UI.
    Rate-limited theo IP; dùng LLM provider do user chỉ định.
    """
    client_ip = str(request.client.host) if request.client else "unknown"
    check_rate_limit(f"ui:{client_ip}")

    if not payload.message.strip():
        raise HTTPException(400, "Message cannot be empty")

    provider_name = payload.provider.lower()
    model_name = payload.model.strip()

    # Khởi tạo LLM provider
    try:
        if provider_name == "openai":
            from app.core.openai_provider import OpenAIProvider
            api_key = payload.api_key or settings.openai_api_key
            if not api_key:
                return JSONResponse(400, content={"error": "Missing API Key", "message": "Set OPENAI_API_KEY"})
            llm = OpenAIProvider(model_name=model_name, api_key=api_key)

        elif provider_name in ("google", "gemini"):
            from app.core.gemini_provider import GeminiProvider
            api_key = payload.api_key or settings.gemini_api_key
            if not api_key:
                return JSONResponse(400, content={"error": "Missing API Key", "message": "Set GEMINI_API_KEY"})
            llm = GeminiProvider(model_name=model_name, api_key=api_key)

        elif provider_name == "local":
            return JSONResponse(400, content={
                "error": "Local provider not available in production Docker",
                "message": "Use openai or gemini provider instead"
            })
        else:
            raise HTTPException(400, f"Unsupported provider: {provider_name}")

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(500, content={"error": "Init error", "message": str(e)})

    # Gọi agent hoặc chatbot
    try:
        from app.tools import ALL_TOOLS
        if payload.mode == "agent":
            from app.agent.agent import ReActAgent
            result = ReActAgent(llm=llm, tools=ALL_TOOLS).run(payload.message)
        else:
            from app.agent.chatbot import ChatbotBaseline
            result = ChatbotBaseline(llm=llm).run(payload.message)

        # Ghi cost (token count từ metrics nếu có)
        usage = result.get("metrics", {})
        check_and_record_cost(
            usage.get("prompt_tokens", len(payload.message.split()) * 2),
            usage.get("completion_tokens", 50),
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(json.dumps({"event": "chat_error", "error": str(e)}))
        return JSONResponse(500, content={"error": "Execution Error", "message": str(e)})


@app.post("/ask", response_model=AskResponse, tags=["API"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """
    **REST API** cho E-commerce Agent.

    Yêu cầu header: `X-API-Key: <key>`

    - `mode=agent` → ReAct agent (Thought-Action-Observation loop, dùng tools)
    - `mode=chatbot` → Chatbot đơn giản (không dùng tools)

    Tools có sẵn: `check_stock`, `apply_discount`, `calculate_shipping`
    """
    # Rate limit theo API key
    check_rate_limit(_key[:8])

    # Budget check
    input_tokens = len(body.question.split()) * 2
    check_and_record_cost(input_tokens, 0)

    logger.info(json.dumps({
        "event": "api_call",
        "mode": body.mode,
        "q_len": len(body.question),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    llm = get_llm_provider()

    try:
        from app.tools import ALL_TOOLS
        if body.mode == "agent":
            from app.agent.agent import ReActAgent
            result = ReActAgent(llm=llm, tools=ALL_TOOLS).run(body.question)
        elif body.mode == "chatbot":
            from app.agent.chatbot import ChatbotBaseline
            result = ChatbotBaseline(llm=llm).run(body.question)
        else:
            raise HTTPException(400, f"mode must be 'agent' or 'chatbot'")

        # Ghi cost
        usage = result.get("metrics", {})
        check_and_record_cost(0, usage.get("completion_tokens", 50))

        return AskResponse(
            question=body.question,
            answer=result.get("answer", ""),
            mode=body.mode,
            model=settings.llm_model if llm else "mock",
            steps=result.get("steps", []),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(json.dumps({"event": "ask_error", "error": str(e)}))
        raise HTTPException(500, f"Agent error: {str(e)}")


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe — platform restart container nếu fail."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "llm_provider": settings.default_provider,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe — load balancer không route vào nếu fail."""
    if not _is_ready:
        raise HTTPException(503, "Not ready yet")
    return {"ready": True, "uptime_seconds": round(time.time() - START_TIME, 1)}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Metrics (protected). Xem usage và budget."""
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "daily_cost_usd": round(_daily_cost, 6),
        "daily_budget_usd": settings.daily_budget_usd,
        "budget_used_pct": round(_daily_cost / settings.daily_budget_usd * 100, 2) if settings.daily_budget_usd else 0,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
    }


# ─────────────────────────────────────────────────────────
# SIGTERM Handler
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "sigterm", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    print(f"\n=== {settings.app_name} ===")
    print(f"Environment : {settings.environment}")
    print(f"LLM Provider: {settings.default_provider} / {settings.llm_model}")
    print(f"API Key     : {settings.agent_api_key[:4]}****")
    print(f"Docs        : http://localhost:{settings.port}/docs")
    print(f"Web UI      : http://localhost:{settings.port}/\n")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
