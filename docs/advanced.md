# Vận hành và demo các tính năng nâng cao

Chạy `python scripts/configure.py` để thêm OPERATIONS_KEY nếu cấu hình cũ chưa có. Các secret đã có được giữ nguyên. Khởi động lại stack để các process nhận cấu hình/source mới:

```powershell
python scripts/start.py --open
```

Có **7 business service**, Broker và Observability: 9 backend process tại 8100–8108, cùng web gateway tại 8080. Mỗi service có DB riêng. `/health` có service và instance; `/internal/metrics` cần service key, không mở trực tiếp cho user.

## Pricing và giá động

Trip gọi Pricing trước khi bắt đầu write transaction. Pricing gọi Driver `/internal/supply` và Trip `/internal/demand` qua HTTP; không đọc DB chéo. Supply là số driver available/presence hợp lệ trong 20km; demand là requested/offered tạo trong 120 giây trong vùng đó.

`base = 12000 + round(km * 8000)`; `multiplier = min(2, 1 + 0.25 * max(0, waiting - available))`. Giá cuối `round(base * multiplier)`. Có thể đặt `DYNAMIC_PRICING=0` để dùng base fare. Khi dependency supply/demand không phản hồi, Pricing ghi rõ `degraded_dependencies` và không surge theo dữ liệu thiếu. Quote được lưu idempotent, không tính lại fare khi message/payment được giao lại. Trip replay cùng key vẫn trả trip cũ kể cả Pricing offline.

Giá ở web là ước tính từ `/api/pricing/quote`; giá cuối được lấy từ response Trip. Chưa tính theo đường bộ hoặc bảng giá chính thức của Grab/Uber.

## Circuit breaker

`CIRCUIT_THRESHOLD=3`, `CIRCUIT_COOLDOWN=2` giây mặc định. Mỗi endpoint có một circuit trong từng process. Lỗi mạng/5xx mở circuit, request tiếp theo bị từ chối nhanh; sau cooldown chỉ một request probe được phép. Probe thành công đóng circuit, thất bại mở lại. 4xx là phản hồi nghiệp vụ, không đếm như outage. NACK có thông báo circuit open sẽ chờ ít nhất cooldown trước retry tiếp theo. Retry vẫn hữu hạn và có DLQ; breaker không thay Saga hoặc dedup.

## Log tập trung và tracing

Collector tại 8108 lưu record vào DB riêng; service gửi qua HTTP service-auth từ hàng đợi telemetry giới hạn 2000 bản ghi. Collector giữ khoảng 50.000 dòng. Đây là observability best-effort: mất collector/queue đầy có thể mất một phần log tập trung, không làm rollback hoặc chặn transaction nghiệp vụ. JSONL từng service vẫn có trên đĩa/stdout Docker.

Log có node, instance, timestamp UTC, correlation_id, trace_id, span_id, parent_span_id, kết quả và duration. HTTP client tạo child span, server nhận parent; outbox envelope giữ producer parent, consumer tạo span tương ứng. Tracing là hiện thực ứng dụng, chưa dùng OpenTelemetry hay traceparent chuẩn W3C. `docs/trace-example.json` có mẫu thực đã chạy.

Trong web mở **Hệ thống → Giám sát vận hành**. Lấy OPERATIONS_KEY từ file `.env` của mình và nhập vào ô mã truy cập; không gửi key vào chat hoặc commit. Dashboard chỉ giữ key trong memory, xóa ô nhập sau kết nối, ngắt kết nối để bỏ phiên xem. Người có user token hoặc SERVICE_KEY không được dùng thay OPERATIONS_KEY. Không mở API redrive/kill từ giao diện người dùng.

Dashboard hiển thị health, metrics, circuit, outbox, inbox, queue, DLQ, instance heartbeat, log gần nhất và trace theo Correlation ID. Dữ liệu cập nhật mỗi 5 giây khi màn hình mở. Instance có log/heartbeat trong 35 giây được đánh dấu online; direct health phát hiện endpoint down sớm hơn. Health/DNS đại diện một endpoint; danh sách instance được tổng hợp từ telemetry.

## Scale Matching

```powershell
docker compose --env-file .env -f deploy/compose.yaml -f deploy/scale.yaml up --build -d
docker compose --env-file .env -f deploy/compose.yaml -f deploy/scale.yaml ps
```

Profile chạy 3 Matching replica, không publish cùng một host port. Mỗi replica có anonymous volume riêng ở `/data` và DB namespace riêng theo hostname/INSTANCE_ID. Chúng claim cùng queue qua network, không dùng file chung để phối hợp. Broker lease/receipt chia công việc; Driver idempotent reserve và lock tài nguyên tại chủ dữ liệu bảo vệ khi redelivery tới replica khác. Crash một Matching không dừng hai instance còn lại. Restart container giữ volume; xóa container/volume thuộc mô hình mất dữ liệu ngoài bảo đảm crash-process. Broker, Driver và các writer SQLite khác chưa HA/scale ngang.

Discovery dùng URL cấu hình và DNS service Docker. Chưa có registry động hoặc leader election; không tuyên bố chạy nhiều instance cho mọi service. Compose cần bản hỗ trợ `!reset`/`!override`.

## Tái lập bằng chứng

```powershell
python scripts/test.py
python tests/test_advanced.py
python tests/test_web.py
python scripts/demo.py --pause
python scripts/advanced_demo.py --pause
```

Các script local tự tạo stack test 9100–9108, replica thêm 9214/9215, web test 9180 và DB riêng trong runtime. Không chạy hai suite dùng cùng cổng song song. A04 ghi `docs/scaling-results.json`: số event xử lý theo từng instance và kiểm tra survivor sau kill. Circuit A01 kiểm state machine có clock giả; R03 kiểm failures thật sau khi Driver bị kill. Các JSON kết quả được tạo bằng lần chạy thực, không viết tay PASS.
