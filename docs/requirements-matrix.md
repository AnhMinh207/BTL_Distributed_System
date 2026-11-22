# Đối chiếu yêu cầu với sản phẩm và bằng chứng

Nguồn: `C:\Bop\COURSE PROJECT SPECIFICATION.pdf`; bản trích `docs/assignment.txt`. Chỉ DS03 cùng các yêu cầu chung áp dụng, không triển khai yêu cầu DS01/02/04.

| Mục đề | Yêu cầu | Triển khai / bằng chứng |
|---|---|---|
| 4.1 | ≥3 tiến trình, identity riêng, network, concurrent requests | 7 OS processes; service names/UUID; ThreadingHTTPServer; test runner ghi PID |
| 4.1 | Không dùng shared memory/file thay network | HTTP giữa mọi service; mỗi DB chỉ service chủ mở; 7 volume Compose riêng |
| 4.1 | Log node/time/event/result | `src/common.py:log`; JSONL tại runtime; correlation_id xuyên Saga |
| 4.2 | Kiến trúc, naming, discovery, message format | `docs/architecture.md`; PORTS, URL env, Compose DNS, envelope UUID |
| 4.2 | Detect offline, timeout/ACK/retry | `/health`, HTTP timeout; Broker receipt/lease; R01–R03, R05 |
| 4.2 | Duplicate/out-of-order và giới hạn | Inbox, request key, event dedup, tombstone, terminal guards; F07/F11/R04/R06; phần giới hạn báo cáo |
| 4.3 | Conflict/consistency/concurrency test | BEGIN IMMEDIATE, version, unique index; C01/C02/C03 |
| 4.4 | Ít nhất 2 tình huống lỗi/phục hồi | R01 Payment crash, R02 Broker crash, R03 Driver retry/DLQ/redrive; thêm R04–R06 |
| 4.5 | Auth, authorization, validate, hash, env secrets, size/log | Identity PBKDF2/HMAC; actor/internal; role/owner; 64 KiB; S01–S03 |
| 7.1–7.2 | ≥4 business services, triển khai độc lập, dữ liệu riêng | 6: Identity, Driver, Trip, Matching, Payment, Notification; broker không tính |
| 7.3 | Đăng ký/đăng nhập, hai role | `src/identity.py`; F01, S01–S03 |
| 7.3 | Driver trạng thái và simulated location | `src/driver.py`; F02; presence lease 300s |
| 7.3 | Passenger tạo ride, find/select driver | Trip → broker → Matching → REST Driver; F03/F05/C01 |
| 7.3 | Driver accept/reject, không double assign | Trip version transitions; atomic reserve; F03/F04/C01/C02 |
| 7.3 | Vòng đời chuyến | requested → offered → accepted → in_progress → awaiting_payment → terminal; F03/F10/S03 |
| 7.3 | Fare và payment mô phỏng | 12.000 VND + 8.000 VND/km Haversine; F08/F03/F09 |
| 7.3 | Notifications hai role | durable notification inbox; GET /notifications; F06 |
| Giao diện bổ sung | Web đầy đủ cho hai vai trò, demo trực quan | `src/web/`, `scripts/web.py`, `scripts/start.py`; đăng ký/login, booking, driver lifecycle, history, payment, notification; `tests/test_web.py` W01–W06 |
| 7.3 | ≥1 REST và ≥1 async MQ flow | Matching → Driver REST; trip.requested queue Matching; R01 chứng minh consumer tắt vẫn enqueue |
| 7.3 | Event ID/idempotency, retry, dedup | UUID, Idempotency-Key, Broker unique ID, inbox; F07/F11/C03/R03 |
| 7.3 | DLQ/error storage, correlation ID | persisted deliveries state dead,error; headers/envelope/logs; R03 |
| 7.3 | Distributed transaction Saga/compensation | trip.cancelled/payment.failed → release driver; F04/F09/F10/R06 |
| 7.4 | Services độc lập, available, request, matching, accept/complete | `scripts/demo.py` cảnh 1 và PID startup; F03 |
| 7.4 | Hai khách đồng thời yêu cầu cùng driver | demo cảnh 2; C01: đúng 1 offered, 1 cancelled |
| 7.4 | Stop service, retry/queue/compensation, restart | demo cảnh 3–6; R01/R02/R03/F09 |
| 7.5 | Nâng cao tùy chọn | Outbox/inbox, geospatial nearest, Docker Compose, correlation tracing logs |
| 9 | ≥8 functional | F01–F11: 11 bài |
| 9 | ≥2 concurrency/conflict | C01–C03: 3 bài |
| 9 | ≥2 fault/recovery | R01–R06: 6 bài |
| 9 | ≥2 security/invalid input | S01–S03: 3 bài, nhiều assertion |
| 9 | ≥1 performance/scalability | Z01: 100 authenticated GET /trips, concurrency 10; số đo `docs/performance.json` |
| 10.1 | Cấu trúc repo, README, env example | Có đầy đủ; deployment/test/demo trong README |
| 10.1 | Commit từng thành viên, GitHub access, release/tag | **Nhóm cần thực hiện thực tế**; không tạo danh tính/commit giả; `docs/submission.md` |
| 10.1 | Bảng phân công | Có template `docs/team.md`, cần họ tên/MSSV/link commit thật |
| 10.2 | Báo cáo PDF, các phần nội dung 1–19 | `docs/report.pdf`; nguồn sinh `scripts/build_docs.py`; bìa cần thông tin nhóm |
| 10.1 | Slides nếu có | `docs/slides.pdf`; có nguồn HTML |
| 11 | Demo ≥3 service, network, concurrent, live failure, logs | script demo 7 tiến trình, kill/restart thật; `docs/demo.md` |
| 11 | Mọi thành viên tham gia demo, vấn đáp | **Nhóm tự chuẩn bị và thực hiện**, checklist phân vai |
| 13 | Citation, tự giải thích, công bố AI | README, báo cáo references và ghi chú AI; câu hỏi vấn đáp trong demo |

Đã xác nhận build/chạy 7 container Docker Compose và 8/8 kịch bản HTTP chọn lọc, gồm kill/restart Payment và Broker (`docs/docker-results.json`). Bộ 24 bài đầy đủ chạy bằng tiến trình Python thật; 8 ca Docker là tập con chạy lại trên môi trường khác. Đăng ký nhóm, tạo repo/quyền truy cập, bổ sung thông tin cá nhân và nộp/vấn đáp cần nhóm thực hiện thực tế.

Bản bổ sung web đã xác nhận **8 container healthy** (web + 7 backend), **6/6 bài proxy** và **14 kiểm tra trình duyệt** trên desktop/mobile. Bằng chứng tại `docs/docker-web-results.json`, `docs/web-test-results.json`, `docs/browser-results.json`; ảnh giao diện ở `docs/ui-*.png`. Đây là các phạm vi kiểm chứng riêng, không gộp browser checks vào số test nghiệp vụ.
