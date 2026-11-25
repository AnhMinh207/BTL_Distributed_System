# Đối chiếu DS03 sau bổ sung

Đối chiếu đúng nội dung 7.1–7.5 người dùng cung cấp. Mục 7.5 là phần nâng cao trong đề; dự án đã bổ sung hiện thực cho tất cả các nhóm tính năng được liệt kê, với phạm vi minh bạch bên dưới.

| Yêu cầu | Hiện thực | Bằng chứng |
|---|---|---|
| 7.1 Triển khai độc lập, REST + MQ | Mỗi entrypoint chạy một service; HTTP JSON; broker durable fan-out/pull/ACK | `src/main.py`, Compose, demo/test process thật |
| 7.2 ≥4 business service | **7**: Identity, Driver, Trip, Matching, Pricing, Payment, Notification; web/broker/collector không tính | Các module tương ứng trong `src/` |
| Dữ liệu riêng, không truy cập DB service khác | SQLite riêng/service; RPC supply/demand/quote thay truy vấn chéo; Matching replica có namespace riêng | `Database`, `pricing.py`, volume Compose |
| Đăng ký/login/phân vai | Password hash/salt, HMAC token, passenger/driver, kiểm ownership | F01, S01–S03 |
| Driver trạng thái/vị trí | available/offline/busy; presence timeout; tọa độ mô phỏng hoặc chọn từ bản đồ | F02/F03 |
| Passenger yêu cầu xe | POST /trips, Idempotency-Key, tối đa một active trip/passenger | F03/F07/C03 |
| Tìm/chọn driver phù hợp | Trong 20 km, presence <300s, gần nhất, tie-break ID | A06, F03/F05 |
| Driver accept/reject | Version + role/ownership và state preconditions | F03/F04/C02 |
| Không gán một tài xế cho hai chuyến | BEGIN IMMEDIATE; chọn và giữ nguyên tử tại Driver; reservation idempotent theo trip | C01 với hai passenger cạnh tranh thật |
| Vòng đời | requested/offered/accepted/in_progress/awaiting_payment/terminal | F03/F10/R06 |
| Fare + simulated payment | Pricing quote riêng, fare được khóa khi đặt; Payment ledger unique trip | F08/F09/A02/A05 |
| Thông báo hai bên | Notification inbox riêng; user chỉ xem thông báo liên quan | F06 |
| REST/gRPC | Matching → Driver reserve; Trip → Pricing → Driver/Trip | HTTP/network trace |
| Async MQ | Business outbox → broker → inbox/handler → ACK | R01: Payment tắt vẫn giữ pending |
| Event ID/idempotency | UUID event, request key+fingerprint, reservation/payment business key | F07/F11/C03 |
| Retry | NACK backoff hữu hạn, lease redelivery; circuit-open delay tránh retry dồn | R03/R05 |
| Dedup | Broker event PK; inbox transaction; Payment trip PK | F11, C03 |
| DLQ/error storage | deliveries state dead + error + attempts; explicit redrive | R03/demo |
| Correlation IDs | Header → trip → envelope → log/trace | A03, `docs/trace-example.json` |
| Saga/compensation | Hủy/từ chối/timeout/payment failed → release driver; tombstone chống đảo thứ tự | F04/F09/F10/R04/R06 |
| 7.4 Start independently | `cluster.py --services <name>`; Docker start/stop từng service | PID startup, Compose |
| Driver online → booking → matching → accept/complete | CLI, web và demo tự động gọi API thật | F03, browser QA |
| Hai passenger cùng yêu cầu một driver | Concurrent POST từ hai user; đúng 1 offered + 1 cancelled | C01/demo cảnh 2 |
| Stop service → retry/queue/compensate → restart | Kill Payment/Broker/Driver thật, kiểm intermediate + final state | R01–R03, demo cảnh 3–6 |

| 7.5 Nâng cao | Phạm vi hiện thực | Bằng chứng / giới hạn |
|---|---|---|
| API Gateway + discovery | Web gateway allowlist, auth forwarding, timeout; service URL env + Docker DNS; health/instance heartbeat | `scripts/web.py`; DNS discovery, chưa dùng registry Consul/Eureka |
| Circuit breaker | closed/open/half-open; chỉ một probe; lỗi 5xx/network tăng failures; 4xx không làm mở circuit | `src/resilience.py`, A01; R03 kiểm metrics failure thật |
| Outbox | Business state + outbox commit cùng transaction; publish lại cùng event ID | R02; inbox chống lặp sau mất ACK |
| Distributed tracing | trace_id/span_id/parent_span_id qua HTTP và event; client/server/consumer durations; xem theo Correlation ID | A03, `trace-example.json`; hiện thực riêng, không tuyên bố OpenTelemetry chuẩn W3C |
| Centralized logging | Collector độc lập, auth service, DB riêng, query theo trace; ship async queue bounded | `src/observability.py`; best-effort, local JSONL vẫn là nguồn khi collector offline; giữ khoảng 50k bản ghi |
| Multiple-instance scaling | Matching là competing consumer; 2 process đã kiểm chứng, Compose profile 3 replica, DB riêng từng replica | A04; `deploy/scale.yaml`; không scale writer SQLite chung file |
| Dynamic pricing | Pricing lấy available drivers và waiting trips trong 20km; hệ số 1–2, tăng 0,25 theo thiếu cung | A02; quote bền/idempotent; thiếu thông tin dependency dùng base fare và ghi degraded |
| Geospatial matching | Haversine, bán kính + nearest + presence; quyết định giữ vẫn nguyên tử | A06; khoảng cách đường chim bay, chưa routing đường bộ |
| Docker/Kubernetes/cloud | Docker Compose đầy đủ, healthcheck, volume riêng, non-root; profile scale | Kiểm chứng Docker riêng; đề cho phép chọn Docker Compose, không bắt buộc thêm K8s/cloud |
| Monitoring dashboard | Health, instance heartbeat, outbox/inbox, circuits, queue/DLQ, central logs và trace spans | Hệ thống → Giám sát vận hành; yêu cầu OPERATIONS_KEY riêng; giao diện đọc, không public broker admin |

Nguồn kết quả: `test-results.json` (24 bắt buộc), `advanced-test-results.json` (6 nâng cao), `web-test-results.json`, `docker-results.json`, `browser-results.json`, `operations-browser-results.json`. Không cộng các ca chạy lặp trên Docker/browser thành các test nghiệp vụ mới. Thông tin nhóm, đóng góp GitHub và vấn đáp vẫn phải do nhóm thực hiện thật.
