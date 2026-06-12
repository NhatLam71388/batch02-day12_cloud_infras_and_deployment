# Solution — Day 12 Lab: Deploy Your AI Agent to Production

> **Nhật Lâm** · vanhung71388@gmail.com · VinUniversity AICB-P1 · 2026-06-12

---

## Part 1: Localhost vs Production

### Exercise 1.1 — 5 Anti-patterns trong `develop/app.py`

| # | Anti-pattern | Vị trí | Vấn đề |
|---|---|---|---|
| 1 | **API key hardcode** | `AGENT_API_KEY = "sk-hardcoded-fake-key..."` | Lộ lên GitHub, không rotate được |
| 2 | **Port cố định** | `uvicorn.run(..., port=8000)` | Xung đột khi deploy nhiều service, không override được |
| 3 | **Debug mode bật** | `uvicorn.run(..., reload=True, debug=True)` | Lộ stack trace cho user, chậm hơn |
| 4 | **Không có health check** | `GET /health → 404` | Platform không biết app còn sống không → không thể tự restart |
| 5 | **Bind localhost** | `host="127.0.0.1"` | Trong container chỉ nhận kết nối nội bộ, bên ngoài không gọi được |

### Exercise 1.3 — So sánh Basic vs Production

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode | Env vars | Secret hardcode lộ ngay khi push GitHub, không rotate được. Env vars cho phép đổi config dev/prod mà không sửa code. |
| Health check | ❌ 404 | ✅ `/health` + `/ready` | Cloud platform gọi `/health` định kỳ — non-200 → restart container tự động. |
| Logging | `print()` | JSON structured | `print()` không có level/timestamp, bản basic còn in API key ra console. JSON parse được bởi log aggregator (Datadog, Loki). |
| Shutdown | Đột ngột | Graceful (SIGTERM) | Khi deploy bản mới platform gửi SIGTERM — graceful cho request đang chạy hoàn thành, user không bị đứt kết nối. |
| Binding | `127.0.0.1` | `0.0.0.0` | Trong container, bind localhost thì bên ngoài không gọi được. |

### Checkpoint 1 ✅

- [x] Hardcode secrets nguy hiểm — lộ qua Git, lộ qua log, không rotate được
- [x] Environment variables — `os.getenv()` trong `config.py`, set qua `.env` / `$env:PORT` / platform dashboard
- [x] Health check — platform dựa vào đây để restart; basic 404, advanced 200 kèm uptime
- [x] Graceful shutdown — lifespan asynccontextmanager: ngừng nhận request mới → hoàn thành in-flight → cleanup → exit 0

> **Bug đã sửa (2026-06-12 thực hành):**
> - `production/` có `python-dotenv` trong requirements nhưng không gọi `load_dotenv()` → thêm vào `app.py` để đọc `.env`
> - JSON log không có hiệu lực do `config.py` gọi `logging.warning()` trước `basicConfig` → fix: thêm `force=True`

---

## Part 2: Docker Containerization

### Exercise 2.1 — Phân tích Dockerfile cơ bản

1. **Base image:** `python:3.11` — bản full distribution (~1GB), chứa cả compiler và tool không cần lúc chạy.
2. **Working directory:** `/app` — mọi lệnh `COPY`/`RUN`/`CMD` phía sau thực thi từ thư mục này.
3. **COPY requirements.txt trước** vì **Docker layer cache**: mỗi lệnh tạo 1 layer, layer chỉ rebuild khi input thay đổi. Code sửa thường xuyên, requirements ít đổi → tách riêng thì `pip install` (chậm nhất) được lấy từ cache khi chỉ sửa code.
4. **CMD vs ENTRYPOINT:** `CMD` là lệnh mặc định, bị ghi đè hoàn toàn khi `docker run image <lệnh khác>`. `ENTRYPOINT` cố định, tham số khi run được **nối thêm** vào sau. Pattern phổ biến: ENTRYPOINT là chương trình chính, CMD là tham số mặc định.

### Exercise 2.2 — Image size

```
Kết quả đo thực tế (2026-06-12):
my-agent:develop = 1.66GB  ← python:3.11 full, single-stage
```

### Exercise 2.3 — Multi-stage build

- **Stage 1 (builder):** `python:3.11-slim` + cài `gcc`, `libpq-dev` để compile deps, `pip install --user` (gói vào `/root/.local`). Stage này **không** được deploy.
- **Stage 2 (runtime):** bắt đầu lại từ `python:3.11-slim` sạch, chỉ `COPY --from=builder /root/.local` + source code. Thêm non-root user `appuser` + `HEALTHCHECK`.
- **Tại sao nhỏ hơn:** image cuối chỉ chứa stage 2 — gcc, apt cache, build tools của stage 1 bị bỏ lại.

```
Kết quả đo thực tế (2026-06-12):
my-agent:develop    1.66GB   ← single-stage, python:3.11 full
my-agent:production  236MB   ← multi-stage, python:3.11-slim  (nhỏ hơn 7×)
```

### Exercise 2.4 — Docker Compose Stack

```
Architecture:
  Internet → Nginx (port 80, rate limit) → agent:8000 (x3, round-robin)
                                                  ↓
                                           Redis (6379, in-memory cache)

Kết quả test:
  curl http://localhost/health → 200 OK (qua nginx)
  curl http://localhost:8000/health → Connection refused (nginx network isolation đúng)
  60 concurrent requests → 49×200 + 11×429 (nginx rate limit burst=20 hoạt động)
```

### Checkpoint 2 ✅

- [x] Dockerfile structure — base image, WORKDIR, layer cache, CMD vs ENTRYPOINT
- [x] Multi-stage — develop 1.66GB → production 236MB, nhỏ hơn 7×; non-root user
- [x] Docker Compose — service discovery qua tên (`redis://redis:6379`), `depends_on` + healthcheck, network isolation
- [x] Debug container — `docker compose logs agent --tail 5`, `docker compose ps`, `docker exec -it <id> /bin/sh`

---

## Part 3: Cloud Deployment

### Exercise 3.1 — Deploy Railway

```bash
railway init              # link project
railway variables set AGENT_API_KEY=secret-key-123
railway up                # build & deploy
railway domain            # assign public URL
```

**Kết quả (2026-06-12):**
```
URL: https://day12-ai-agent-production-15c8.up.railway.app
GET /health → 200 {"status":"ok","environment":"production",...}
GET /       → 200 (web UI)
POST /ask   → 200 (với API key)
```

### Exercise 3.2 — Deploy Render

Dùng `render.yaml` Blueprint:
```yaml
services:
  - type: web
    name: ai-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
  - type: redis
    name: agent-cache
```

**Kết quả (2026-06-12):** Deploy thành công qua Blueprint từ GitHub repo. Render tạo đúng 2 service: web `ai-agent` (Singapore, free) + Key Value `agent-cache`. `/health` → 200.

### Exercise 3.3 — GCP Cloud Run (Discussion)

| Platform | Pros | Cons |
|----------|------|------|
| Railway | Nhanh, đơn giản, free $5 credit | Tốn credit nhanh nếu chạy 24/7 |
| Render | Free tier tốt (750h), PostgreSQL free | Sleep sau 15 phút inactivity (free tier) |
| Cloud Run | Scale to zero, pay per request, Google infra | Phức tạp hơn (IAM, Artifact Registry, cold start) |

**Khi nào dùng Cloud Run:** Production thật, traffic không đều, cần scale to zero để tiết kiệm chi phí, tích hợp với Google Cloud ecosystem (BigQuery, Pub/Sub...).

### Checkpoint 3 ✅

- [x] Deploy Railway — project `day12-ai-agent`, public URL hoạt động, test `/health` + `/ask` qua Internet
- [x] Deploy Render — Blueprint từ render.yaml, 2 service (web + redis), `/health` → 200
- [x] Set environment variables — Railway: `railway variables set`; Render: dashboard / `envVars` trong render.yaml
- [x] Xem logs — Railway: `railway logs`; Render: tab Logs trên dashboard

---

## Part 4: API Security

### Exercise 4.1 — API Key Authentication

- **API key check ở đâu:** FastAPI `Depends(verify_api_key)` trong decorator endpoint — framework inject trước khi handler chạy. So sánh với `os.getenv("AGENT_API_KEY")`.
- **Nếu thiếu header:** `401 {"detail":"X-API-Key header missing"}`
- **Nếu sai key:** `403 {"detail":"Invalid API key"}`
- **Rotate key:** Đổi env var `AGENT_API_KEY` + restart — không sửa code.

```
Test thực tế (2026-06-12):
POST /ask  (no header)           → 401
POST /ask  X-API-Key: wrong      → 403
POST /ask  X-API-Key: secret-key → 200
```

### Exercise 4.2 — JWT Authentication

JWT flow: `login → server ký HS256(username+role+exp) → client lưu token → gửi trong Authorization: Bearer header mỗi request → server verify signature + exp → extract username/role`.

```
POST /auth/token {"username":"student","password":"demo123"}
→ {"access_token":"eyJ...","token_type":"bearer","expires_in_minutes":60}

POST /ask  Authorization: Bearer eyJ...
→ 200 {"answer":"...","usage":{"requests_remaining":9,...}}
```

### Exercise 4.3 — Rate Limiting

- **Algorithm:** **Sliding Window Counter** — `ZADD` timestamps vào Redis sorted set, `ZREMRANGEBYSCORE` xóa timestamps > 60s cũ, `ZCARD` đếm số request còn trong window.
- **Tại sao Sliding > Fixed Window:** Fixed window có "burst đôi" ở biên phút (59 req ở :59s + 59 req ở :01s tiếp theo = 118 req/2s). Sliding window luôn chính xác.
- **Limit:** user = 10 req/min; admin = 100 req/min (dựa vào `role` từ JWT).

```
Request 1-10  → 200 OK (requests_remaining: 9...0)
Request 11    → 429 {"detail":"Rate limit exceeded. Retry after 58s"}
               Header: Retry-After: 58
```

### Exercise 4.4 — Cost Guard

- User budget: **$1/ngày**; Global budget: **$10/ngày** (lưu Redis, reset 0h mỗi ngày)
- Token estimate: số từ × 2. Giá: $0.002/1K input + $0.006/1K output (GPT-4o-mini)
- Vượt budget → `402 Payment Required`
- `/me/usage` xem usage cá nhân; `/admin/stats` xem global (admin only, 403 nếu không đúng role)

### Checkpoint 4 ✅

- [x] API key authentication — 401 (no key), 403 (wrong key), 200 (valid)
- [x] JWT flow — login → HS256 token (60 min) → Bearer header → verify_token dependency
- [x] Rate limiting — Sliding Window Counter, 10/min user, 100/min admin; test 11 requests → request 11 nhận 429 + Retry-After
- [x] Cost guard — $1/day per user, $10/day global, token counting, 402 khi vượt

> **Bug đã sửa:** `response.headers.pop("server", None)` → `MutableHeaders` không có `.pop()` → fix: `if "server" in response.headers: del response.headers["server"]`

---

## Part 5: Scaling & Reliability

### Exercise 5.1 — Health Checks

```python
@app.get("/health")
def health():
    """Liveness probe — process còn sống không?"""
    return {"status": "ok", "instance_id": INSTANCE_ID, "uptime_seconds": uptime}

@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic không?"""
    try:
        redis_client.ping()
        return {"ready": True, "instance": INSTANCE_ID}
    except:
        raise HTTPException(503, "Redis not available")
```

**Phân biệt liveness vs readiness:**
- `/health` (liveness): đơn giản — process còn chạy không? Platform **restart** container nếu fail.
- `/ready` (readiness): nghiêm ngặt hơn — check Redis/DB, đảm bảo instance xử lý được request. Load balancer **không route** vào nếu fail (ví dụ: đang khởi động, đang nạp model).

```
Test thực tế:
GET /health → 200 {"status":"ok","instance_id":"instance-3af854","uptime_seconds":12.4,"redis_connected":true}
GET /ready  → 200 {"ready":true,"instance":"instance-3af854"}
             (nếu Redis down → 503 "Redis not available")
```

### Exercise 5.2 — Graceful Shutdown

Dùng **FastAPI lifespan** (asynccontextmanager):

```python
@asynccontextmanager
async def lifespan(app):
    logger.info(f"Starting {INSTANCE_ID}")
    yield                          # ← app chạy ở đây
    logger.info(f"Shutting down")  # ← SIGTERM → chạy phần này sau khi hết in-flight requests
```

Uvicorn nhận SIGTERM: **ngừng nhận kết nối mới** → **đợi request đang xử lý xong** → chạy cleanup block → exit 0. Không mất request trong flight.

### Exercise 5.3 — Stateless Design

```python
def save_session(session_id, data, ttl=3600):
    redis_client.setex(f"session:{session_id}", ttl, json.dumps(data))

def load_session(session_id):
    data = redis_client.get(f"session:{session_id}")
    return json.loads(data) if data else {}
```

**Tại sao:** Nếu lưu state trong memory (`dict`), instance A có conversation của user nhưng instance B không có → requests bị route sang B sẽ mất context. Lưu Redis → mọi instance đều đọc được → horizontal scaling không giới hạn.

### Exercise 5.4 — Load Balancing

```bash
docker compose up -d --build --scale agent=3
```

Khởi động theo thứ tự: Redis healthy → 3 agent instances → Nginx.

Nginx `nginx.conf` dùng `upstream agent { server agent:8000; }` — Docker Compose DNS tự resolve thành 3 IP của service `agent`, round-robin giữa chúng.

### Exercise 5.5 — Test Stateless

```
python test_stateless.py

Session ID: 2492d17d-e32b-4758-83ec-53959e36dc72

Request 1: [instance-34b2fb]   Q: What is Docker?
Request 2: [instance-3af854]   Q: Why do we need containers?
Request 3: [instance-3a26c4]   Q: What is Kubernetes?
Request 4: [instance-34b2fb]   Q: How does load balancing work?
Request 5: [instance-3af854]   Q: What is Redis used for?

Instances used: {instance-34b2fb, instance-3af854, instance-3a26c4}
✅ All requests served despite different instances!
Total messages in history: 10 (5 user + 5 assistant)
✅ Session history preserved across all instances via Redis!
```

**Demo graceful shutdown:**
```bash
docker stop production-agent-1
# → agent-2 và agent-3 vẫn healthy
# → 3 requests tiếp chỉ thấy instance-34b2fb và instance-3a26c4
# → Zero errors — nginx tự loại agent-1 khỏi upstream
```

### Checkpoint 5 ✅

- [x] Health + readiness checks — `/health` liveness (200 khi process alive), `/ready` readiness (503 nếu Redis down)
- [x] Graceful shutdown — FastAPI lifespan asynccontextmanager: SIGTERM → hoàn thành in-flight → cleanup → exit 0
- [x] Stateless — session lưu Redis TTL 3600s (`setex`); 5 requests → 3 instance IDs → history liên tục ✅
- [x] Load balancing — `--scale agent=3`; nginx round-robin qua Docker DNS; kill 1 instance → zero errors
- [x] Test stateless — 3 instance IDs khác nhau, 10 messages đúng thứ tự, storage="redis" ✅

---

## Tóm tắt

| Part | Kết quả |
|------|---------|
| Part 1: Localhost vs Production | ✅ 5 anti-patterns, bảng so sánh, env vars, graceful shutdown |
| Part 2: Docker | ✅ Layer cache, multi-stage 1.66GB→236MB, non-root user, Compose stack |
| Part 3: Cloud Deploy | ✅ Railway live + Render Blueprint deploy |
| Part 4: API Security | ✅ API key 401/403, JWT HS256, sliding window 429, cost guard 402 |
| Part 5: Scaling | ✅ Liveness/readiness, graceful shutdown, Redis sessions, nginx LB, test_stateless.py |
