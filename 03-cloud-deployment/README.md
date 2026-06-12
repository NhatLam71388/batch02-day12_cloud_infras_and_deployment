# Section 3 — Cloud Deployment Options

## 3 Tier: Chọn Platform Theo Nhu Cầu

| Tier | Platform | Khi nào dùng | Thời gian deploy |
|------|----------|-------------|-----------------|
| 1 | Railway, Render | MVP, demo, học | < 10 phút |
| 2 | AWS ECS, Cloud Run | Production | 15–30 phút |
| 3 | Kubernetes | Enterprise, large-scale | Vài giờ setup |

---

## railway/ — Deploy < 5 Phút

Không cần server config. Kết nối GitHub → Auto deploy.

```
railway/
├── railway.toml        # Railway config
├── Procfile            # Define start command
├── app.py              # Agent (Railway-ready)
└── requirements.txt
```

### Các bước deploy Railway:
1. `railway login` (hoặc qua browser)
2. `railway init`
3. `railway up`
4. Nhận URL dạng `https://your-app.up.railway.app`

---

## render/ — render.yaml (Infrastructure as Code)

Định nghĩa toàn bộ infrastructure trong 1 YAML file.

```
render/
├── render.yaml         # Khai báo service, env vars, disk
└── app.py
```

---

## production-cloud-run/ — GCP Cloud Run + CI/CD

Production-grade. Tự động build và deploy khi push code.

```
production-cloud-run/
├── cloudbuild.yaml     # CI/CD pipeline
├── service.yaml        # Cloud Run service definition
└── README.md           # Hướng dẫn chi tiết
```

---

## Câu hỏi thảo luận

1. Tại sao serverless (Lambda) không phải lúc nào cũng tốt cho AI agent?
2. "Cold start" là gì? Ảnh hưởng thế nào đến UX?
3. Khi nào nên upgrade từ Railway lên Cloud Run?

### Trả lời (thực hành 2026-06-12)

1. **Serverless không phải lúc nào cũng hợp với AI agent vì:** (a) Lambda có timeout cứng (15 phút max, API Gateway 29s) trong khi LLM call + agent loop có thể chạy lâu; (b) agent thường cần giữ kết nối streaming — mô hình request/response ngắn của serverless không khớp; (c) cold start của serverless cộng thêm thời gian load model/khởi tạo connection làm độ trễ tệ hơn; (d) chi phí theo invocation có thể đắt hơn container chạy nền khi traffic đều.

2. **Cold start** là độ trễ khi platform phải khởi động instance mới từ 0 (kéo image, start process, init app) vì không có instance nào đang chạy. Trải nghiệm thực tế ngay trong lab này: Render free tier cho app ngủ sau 15 phút — request đầu tiên sau đó mất ~30s mới có phản hồi, user tưởng app chết. Cách chữa: giữ tối thiểu 1 instance luôn thức (`min-instances=1` trong cloudbuild.yaml của Cloud Run — đánh đổi bằng tiền).

3. **Upgrade từ Railway lên Cloud Run khi:** cần auto-scale theo traffic thật (Cloud Run scale 0→N theo request, cấu hình `containerConcurrency`); cần CI/CD đầy đủ (test trước khi deploy — cloudbuild.yaml); cần secrets management chuẩn (Secret Manager thay vì env vars); cần SLA/compliance cho khách hàng doanh nghiệp; hoặc chi phí Railway vượt ~$20-50/tháng — lúc đó pay-per-use của Cloud Run thường rẻ hơn. Còn làm MVP/demo/đồ án thì Railway/Render đủ và nhanh hơn nhiều.
