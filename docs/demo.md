# Kịch bản trình bày và demo DS03

## Demo giao diện trực quan

Chạy `python scripts/start.py --open`, mở **http://127.0.0.1:8080**. Chọn **Demo → Chuẩn bị demo** ở góc trên, ở vai trò **Hành khách** nhấn **Đặt xe ngay**. Chuyển sang **Tài xế**, nhấn **Chấp nhận chuyến → Đã đón khách · Bắt đầu → Hoàn thành chuyến**. Chuyển lại Hành khách để xem hoàn tất, lịch sử, thanh toán và thông báo. **Demo → Chạy chuyến mẫu** tự chạy toàn bộ luồng thật và hiển thị tiến độ bảy bước.

Để trình bày lỗi, dừng một dịch vụ từ terminal rồi mở mục **Trạng thái hệ thống** trên web; booking/payment sẽ chờ hoặc báo lỗi theo giai đoạn. Các cảnh kill/retry/DLQ bên dưới vẫn chạy được độc lập để chứng minh cơ chế chi tiết. Không mở API quản trị broker ra giao diện người dùng.

## Chuẩn bị

Đọc README, chạy `python scripts/test.py`. Bảo đảm cổng 9100–9106 trống; script demo dùng dữ liệu thử riêng và không đụng cluster 8100–8106. Mở hai terminal: một chạy `python scripts/demo.py --pause`, terminal kia xem log. Đầu script in PID và cuối script in thư mục log đầy đủ. Có thể xác định thư mục đang chạy bằng PowerShell:

```powershell
$run = Get-ChildItem .\runtime -Directory -Filter 'test-*' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content (Join-Path $run.FullName 'logs\trip.jsonl') -Tail 20 -Wait
```

Mở terminal khác cho `broker.jsonl`, `matching.jsonl`, `payment.jsonl` theo cách tương tự. Ctrl+C chỉ dừng xem log. Script demo thực sự kill/restart child process, không chỉ đặt biến giả lập lỗi. `scripts/test.py` giữ nguyên log ở runtime sau chạy; có thể dùng một correlation ID để tìm các dòng của cùng Saga:

```powershell
Select-String -Path (Join-Path $run.FullName 'logs\*.jsonl') -Pattern '<CORRELATION_ID>'
```

## Phân bổ thời gian

Giới thiệu 3–5 phút: bài toán, 6 business service/DB riêng, REST + MQ, nhất quán cục bộ và eventual. Demo 7–10 phút theo 6 cảnh bên dưới; mỗi cảnh bấm Enter sau khi giải thích bằng chứng. Vấn đáp khoảng 5 phút. Dùng slides kèm theo, điều chỉnh theo quy định giảng viên.

| Cảnh | Thao tác thực trong script | Kết quả và log cần chỉ ra |
|---|---|---|
| 1, 1–2 phút | Driver available, passenger request; Matching reserve; accept/start/complete | Trip offered → accepted → in_progress → awaiting_payment → completed; payment ledger paid; driver available; `trip.transition`, `event.enqueued`, `event.processed` |
| 2, 1 phút | ThreadPool gửi hai POST /trips từ hai passenger, chỉ một driver gần | Đúng 1 offered và 1 cancelled, active_trip của driver bằng chuyến thắng; giải thích khóa giao dịch Driver |
| 3, 1–2 phút | Kill Payment, complete chuyến, kiểm tra queue, restart Payment | Trước restart awaiting_payment và pending payment; sau restart completed và available; PID Payment mới |
| 4, 1 phút | Kill Broker, tạo chuyến, restart Broker | Trip vẫn commit requested; outbox.retry, sau restart outbox.published; matching tiếp tục, chuyến hoàn tất |
| 5, 1–2 phút | Kill Driver trước booking, chờ Matching retry đến DLQ, restart Driver, redrive | `event.retry`, delivery.dead, attempts=3 ở demo; delivery.redrive; chuyến được offer và hoàn tất |
| 6, 1 phút | Tạo booking payment_mode=decline và hoàn tất | ledger declined, Trip payment_failed, Driver available; giải thích compensation không thể hoàn tác chuyến vật lý |

Demo assertions sai sẽ dừng script với lỗi thay vì tiếp tục in PASS. Có thể đọc chi tiết thao tác trong `tests/test_system.py`, vì demo tái sử dụng đúng kịch bản được kiểm chứng. Test R04/R05/R06 bổ sung minh họa đảo thứ tự, lease hết hạn và Saga timeout nếu còn thời gian.

## Câu hỏi vấn đáp nên tự trả lời

1. Vì sao broker là MQ dù producer/consumer dùng HTTP? Producer chỉ chờ lưu bền; consumer độc lập, có durable delivery, ACK, lease, retry và DLQ.
2. Vì sao không double-book? Mọi reserve cho Driver đi qua một giao dịch BEGIN IMMEDIATE; chỉ available/active_trip NULL được chọn và cập nhật trong cùng transaction.
3. Vì sao không dùng transaction chung giữa các DB? Mỗi service tự quản dữ liệu, Saga chuyển trạng thái và bù qua event; không có distributed lock toàn hệ thống.
4. Crash đúng sau reserve nhưng trước ACK xử lý thế nào? REST idempotent theo trip; message giao lại; inbox/outbox bảo đảm tác dụng cục bộ không lặp.
5. Cancellation đến trước reserve? Reservation tombstone khiến reserve trả null; kết quả matching đến muộn không hồi sinh chuyến terminal.
6. Sự kiện gửi lại sau mất ACK? Event ID dedup tại broker; inbox dedup tại consumer; payment unique trip_id.
7. Queue delivery có exactly once không? Không; at-least-once trong giới hạn retry, sau đó DLQ cần vận hành. Tác dụng idempotent theo event và khóa nghiệp vụ.
8. Nếu broker hỏng đĩa? Prototype chưa có replication/HA; không bảo đảm phục hồi mất đĩa. Persistence chỉ kiểm chứng crash tiến trình.
9. API Gateway có tính vào business service không? Không; dự án đã có 6 business service và không cần Gateway để đủ tiêu chí.
10. Hiệu năng đo gì? 100 GET /trips có auth, 10 client đồng thời, localhost; không suy ra throughput booking hoặc quy mô triển khai thực.

Mỗi thành viên trình bày phần việc thật theo `docs/team.md`, đồng thời hiểu kiến trúc chung. Không chỉ đọc slides; nên mở phần code transaction/outbox/inbox và log tương ứng khi giảng viên hỏi.
