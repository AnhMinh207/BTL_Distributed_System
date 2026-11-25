# Thông tin nhóm — cần điền dữ liệu thật

- Học phần: Distributed Systems
- Đề tài: DS03 — Ride-hailing microservices system simulating Grab/Uber
- Lớp: [điền]
- Giảng viên: [điền]
- Tên nhóm: [điền]
- Repository GitHub: https://github.com/AnhMinh207/BTL_Distributed_System

Nhóm không quá 3 thành viên. Bảng dưới là phân công đề xuất, chưa phải bằng chứng đã đóng góp.

| Thành viên / MSSV | Phần việc đề xuất | Bằng chứng cần bổ sung |
|---|---|---|
| Nguyễn Khắc Anh Minh / B23DCCE065 | Identity, Driver, xác thực/phân quyền; giữ tài xế nguyên tử; giao diện khách/tài xế, Gateway, OpenStreetMap và tìm địa điểm | Commit/PR thật; kiểm thử tài khoản/quyền, vị trí, web và geocoding; demo tài xế online và chọn điểm đón/đến |
| Trịnh Gia Huy / B23DCCE047 | Trip, Matching, Pricing; vòng đời/version, idempotency, Saga/timeout, kiểm soát đồng thời và giá động | Commit/PR thật; kiểm thử vòng đời, request trùng, tranh chấp, timeout và pricing; demo đặt/nhận/hoàn thành chuyến |
| Nguyễn Thế Khải / B23DCAT144 | Broker, Payment, Notification; retry/dedup/DLQ, circuit breaker, logging/tracing/dashboard, Docker Compose và scale Matching | Commit/PR thật; demo lỗi/khôi phục, thanh toán, thông báo và trace; kết quả kiểm thử và thực nghiệm |

Task, mã nguồn, kiểm thử và phần demo chi tiết được phân công tại [README — Phân công công việc cho 3 thành viên](../README.md#phân-công-công-việc-cho-3-thành-viên). Cả nhóm cùng review mã dùng chung, tích hợp, viết báo cáo/slide và chuẩn bị vấn đáp theo phần việc phụ trách.

Nếu nhóm 1–2 người, điều chỉnh phân công để tất cả phần việc có người phụ trách. Mỗi người phải hiểu kiến trúc chung và giải thích được phần việc của mình. Không tạo commit giả dưới danh tính thành viên.
