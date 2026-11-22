# Giao diện web GoRide

## Khởi động và xem demo

```powershell
python scripts/start.py --open
```

Mở **http://127.0.0.1:8080**. Giữ terminal chạy. Nếu đã có backend ở các terminal khác, `start.py` sẽ kiểm tra `/health` và dùng lại thay vì tạo tiến trình trùng cổng. Khi thoát chỉ dừng các tiến trình do chính launcher tạo.

Muốn chỉ thêm web vào backend đang chạy: `python scripts/web.py`. Với Docker Compose, chạy `up --build -d` như README rồi mở cùng địa chỉ 8080. Không chạy web local đồng thời với web Docker trên cùng cổng.

## Hai cách trải nghiệm

**Tự thao tác:** nhấn Chuẩn bị demo, chọn Hành khách, đặt xe, đổi vai trò Tài xế, chấp nhận, bắt đầu và hoàn tất. Đổi lại Hành khách để xem kết quả và các giao dịch/thông báo. Chuẩn bị demo đăng ký hai tài khoản ngẫu nhiên bằng Identity, cập nhật Driver available qua REST, rồi lưu token của hai vai trò trong phiên tab. Mật khẩu ngẫu nhiên không lưu hoặc log; tài khoản demo chỉ phục vụ phiên này, có thể tạo mới nếu mất phiên.

**Tự động:** nút mũi tên ở thẻ “Xem một chuyến đi trọn vẹn” chạy bảy bước qua API thật: tài khoản/tài xế, tạo booking, đợi matching, accept, start, complete, đợi payment terminal. Tiến độ và lỗi được hiển thị. Demo tạo tài khoản mới riêng; không thay đổi logic backend hoặc trả kết quả giả. Khi chuyến đang hoạt động, không cho khởi tạo phiên demo mới để tránh bỏ dở chuyến hiện tại.

Người dùng cũng có thể đăng ký/đăng nhập thủ công, thêm tài khoản vai trò còn lại hoặc dùng hai tab/cửa sổ độc lập. Phiên được lưu bằng `sessionStorage`, không chứa password. Một tab có thể chuyển hai vai trò; mỗi lần gọi API chỉ gửi token của tài khoản thực hiện thao tác. Token và quyền sở hữu vẫn được backend kiểm tra.

## Các màn hình

| Màn hình | Thao tác |
|---|---|
| Đăng nhập / tạo tài khoản | Chọn passenger hoặc driver khi đăng ký; hiện/ẩn mật khẩu; báo lỗi nhập liệu/xác thực |
| Hành khách | Chọn địa điểm mẫu hoặc nhập tọa độ; chọn trên sơ đồ; ước tính giá; tạo/hủy chuyến |
| Tài xế | Nhập vị trí; online/offline; giữ busy khi có chuyến; accept/reject/start/complete |
| Hành trình | Trạng thái tự cập nhật, timeline, giá server, mã chuyến và correlation ID |
| Lịch sử | Các chuyến của user; mở lại chi tiết chuyến; ưu tiên hiển thị chuyến đang hoạt động |
| Thanh toán | Ledger thật của Payment; tổng paid, số thành công/bị từ chối; không thu tiền thật |
| Thông báo | Hộp thư thật của Notification, chỉ dữ liệu liên quan user |
| Hệ thống | Health của 7 backend; phản ánh service dừng; không có nút quản trị broker công khai |

## Kiến trúc và xử lý lỗi

`src/web/` chứa HTML/CSS/JS/SVG, không cần framework/CDN. `scripts/web.py` phục vụ asset và public proxy `/api/{service}/{path}` cùng origin. Proxy chỉ cho phép danh sách route cụ thể. Nó không truy cập SQLite, không forward service key, không cho gọi broker/internal/reserve và không được tính là business microservice.

Browser polling dữ liệu user mỗi 2 giây, health mỗi 10 giây khi tab đang hiển thị. Tài xế đang nhận chuyến gửi vị trí/presence tối thiểu khoảng mỗi phút khi tab được mở và đang chọn vai trò tài xế. Tab ẩn không gửi heartbeat; sau 300 giây Driver tự loại khỏi candidate vì presence cũ. Trạng thái busy không bị heartbeat đổi thành available.

POST booking giữ cùng idempotency key khi retry payload không đổi sau timeout, kể cả reload tab. Lệnh accept/start/complete/cancel luôn gửi version từ response mới nhất; lỗi 409 tải lại trạng thái để người dùng quyết định tiếp. Nếu dịch vụ offline, frontend hiển thị thông báo lỗi và giữ dữ liệu gần nhất; trạng thái cuối vẫn do backend và Saga quyết định.

Proxy giới hạn body 64 KiB, chặn POST từ Origin khác, dùng allowlist asset để không đọc file tùy ý. CSP chỉ cho script cùng origin, chặn frame, thêm nosniff/no-store. Không có service secret trong JavaScript. Các giới hạn TLS/rate-limit/token revoke của backend vẫn áp dụng như tài liệu kiến trúc.

Sơ đồ là SVG minh họa, vị trí marker được chiếu từ tọa độ nhập; đường nối không phải đường đi thực. Các địa điểm mẫu chỉ cung cấp tọa độ mô phỏng. Giá ước tính phía web là tham khảo; server Trip tính và lưu giá cuối cùng.

## Kiểm chứng

```powershell
python tests/test_web.py
node --check src/web/app.js
```

Kiểm thử tùy chọn bằng trình duyệt thật:

```powershell
npm install --prefix runtime/browser-qa playwright --no-save --no-package-lock
python scripts/start.py
# Terminal khác
node scripts/browser_qa.cjs
```

Script dùng Edge đã cài trên Windows; có thể đặt `BROWSER_PATH` cho Chrome/Edge khác. Không cần tải browser hoặc thêm dependency cho ứng dụng. Kết quả lưu `docs/browser-results.json`; ảnh desktop/tài xế/mobile tại `docs/ui-*.png`. Backend 24 bài, web proxy 6 bài và browser checks được báo cáo riêng.
