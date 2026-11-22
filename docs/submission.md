# Checklist bàn giao thật

## Phần có trong workspace

- Mã nguồn 6 business service + broker riêng; local multi-process runner và Docker Compose.
- CLI đăng ký, đăng nhập, cập nhật tài xế, đặt/chấp nhận/từ chối/bắt đầu/hoàn thành/hủy chuyến, payment, notification.
- Bộ kiểm thử chức năng, đồng thời, lỗi, bảo mật và hiệu năng; kết quả thực đo dạng JSON.
- Báo cáo PDF, slides PDF, kiến trúc/API, ma trận yêu cầu, kịch bản demo, mẫu phân công.
- `.env.example` không chứa secret; `.env` và runtime được ignore.

## Nhóm phải hoàn thiện trước nộp

1. Điền họ tên, MSSV chính xác, lớp, giảng viên, tên nhóm, URL repo trong `docs/team.md`. Nhóm ≤3 người; xác nhận đăng ký với giảng viên theo file đề. Không tự điền các dữ liệu này từ suy đoán.
2. Đọc và hiểu code, review các giới hạn; mỗi thành viên thực hiện phần việc của mình và có commit/PR thực. Báo cáo có công bố AI hỗ trợ; nhóm chịu trách nhiệm kiểm chứng theo mục 13.
3. Chạy lại `python scripts/test.py`, kiểm tra 24 bài và các file JSON, xem log của lỗi/phục hồi. Đã xác nhận 8/8 ca Docker chọn lọc trên máy tạo dự án; nhóm nên chạy lại Compose và `python scripts/docker_smoke.py --project <TEN_PROJECT>` trên máy demo. Script Docker sẽ kill/start Payment và Broker của đúng project được chỉ định.
4. Tái sinh tài liệu sau khi đổi thông tin/kết quả: `python scripts/build_docs.py`, rồi dùng chức năng print PDF hoặc `python scripts/export_pdf.py` nếu có Chrome/Edge. Kiểm tra bìa, font tiếng Việt, số trang, số đo thực tế.
5. Tạo GitHub repo theo tài khoản nhóm. Kiểm tra `git status`, bảo đảm không add `.env`, password/token/log nhạy cảm. Chỉ đẩy source và tài liệu được review; grant instructor access nếu private.
6. Tạo tag/release cuối, ví dụ `git tag v1.0.0` rồi `git push origin v1.0.0`, sau khi cả nhóm xác nhận phiên bản cuối. Không coi một thư mục local là đã nộp GitHub.
7. Demo thật 7–10 phút, có ≥3 process, network, concurrency, live failure và logs; mọi thành viên tham gia; chuẩn bị vấn đáp.

Theo file đề: deadline source/report **22/11/2026**; các buổi demo/vấn đáp **23/11/2026** và **30/11/2026**. Các mốc này được chép từ tài liệu người dùng cung cấp, cần theo thông báo chính thức nếu giảng viên cập nhật. Dự án chưa tự đăng ký nhóm, tạo repo, push code hay nộp bài.
