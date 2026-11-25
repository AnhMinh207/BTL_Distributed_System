# Giao diện web GoRide

## Bản đồ thật OpenStreetMap

Ứng dụng dùng **Leaflet 1.9.4** và tile đường phố **OpenStreetMap**, không cần API key, Google Cloud hoặc Billing. Chạy `python scripts/start.py --open` rồi mở http://127.0.0.1:8080. Cần Internet để tải dữ liệu đường phố và tìm địa chỉ trực tuyến.

Nhấn **Chọn trên bản đồ** bên dưới điểm đón hoặc điểm đến, rồi bấm vào đường phố. Kéo ghim **A** (điểm đón) / **B** (điểm đến) để tinh chỉnh. Ghim **T** là tài xế. Tọa độ được lấy trực tiếp từ sự kiện địa lý của Leaflet; khi chọn trên map, ô địa điểm ghi tọa độ chính xác, không tự bịa số nhà/tên đường. Muốn chọn theo tên địa chỉ, gõ vào ô tìm kiếm và chọn kết quả Photon.

Giữ ghi nguồn OpenStreetMap hiển thị trên bản đồ. Tile được tải trực tiếp bằng HTTPS, dùng cache mặc định của browser, gửi Referer phù hợp; không prefetch, bulk download hoặc proxy tile. Máy chủ công cộng chỉ phù hợp demo tương tác lưu lượng nhỏ; không có bảo đảm SLA. `OSM_TILE_URL` cho phép chuyển sang nhà cung cấp HTTPS khác khi cần; cập nhật attribution nếu dùng nguồn dữ liệu khác. [Tile usage policy](https://operations.osmfoundation.org/policies/tiles/).

Leaflet được lưu trong `src/web/vendor/leaflet/`, kèm LICENSE; không phải tải thư viện từ CDN khi mở app. [Leaflet](https://leafletjs.com/). Kiểm chứng thực: `node scripts/osm_qa.cjs` (tile thật, click và drag bằng con trỏ), kết quả `docs/osm-map-results.json` và ảnh `docs/ui-osm-*.png`.

## Khởi động và xem demo

```powershell
python scripts/start.py --open
```

Mở **http://127.0.0.1:8080**. Giữ terminal chạy. Nếu đã có backend ở các terminal khác, `start.py` sẽ kiểm tra `/health` và dùng lại thay vì tạo tiến trình trùng cổng. Khi thoát chỉ dừng các tiến trình do chính launcher tạo.

Muốn chỉ thêm web vào backend đang chạy: `python scripts/web.py`. Với Docker Compose, chạy `up --build -d` như README rồi mở cùng địa chỉ 8080. Không chạy web local đồng thời với web Docker trên cùng cổng.

## Hai cách trải nghiệm

**Tự thao tác:** mở menu **Demo** ở góc trên, nhấn **Chuẩn bị demo**, chọn Hành khách, đặt xe, đổi vai trò Tài xế, chấp nhận, bắt đầu và hoàn tất. Đổi lại Hành khách để xem kết quả và các giao dịch/thông báo. Chuẩn bị demo đăng ký hai tài khoản ngẫu nhiên bằng Identity, cập nhật Driver available qua REST, rồi lưu token của hai vai trò trong phiên tab. Mật khẩu ngẫu nhiên không lưu hoặc log; tài khoản demo chỉ phục vụ phiên này, có thể tạo mới nếu mất phiên.

**Tự động:** chọn **Demo → Chạy chuyến mẫu** để chạy bảy bước qua API thật: tài khoản/tài xế, tạo booking, đợi matching, accept, start, complete, đợi payment terminal. Tiến độ và lỗi được hiển thị. Demo tạo tài khoản mới riêng; không thay đổi logic backend hoặc trả kết quả giả. Khi chuyến đang hoạt động, không cho khởi tạo phiên demo mới để tránh bỏ dở chuyến hiện tại.

Giao diện ưu tiên chọn địa điểm và theo dõi chuyến. Nút **Đăng nhập** mở hộp thoại đăng nhập/đăng ký; có thể đóng bằng nút × hoặc Escape. Tọa độ nâng cao nằm trong **Nhập tọa độ**. Correlation ID/version ở **Chi tiết chuyến**. Điện thoại có bản đồ phía trên, bảng đặt xe bên dưới và thanh điều hướng ở đáy màn hình.

Người dùng cũng có thể đăng ký/đăng nhập thủ công, thêm tài khoản vai trò còn lại hoặc dùng hai tab/cửa sổ độc lập. Phiên được lưu bằng `sessionStorage`, không chứa password. Một tab có thể chuyển hai vai trò; mỗi lần gọi API chỉ gửi token của tài khoản thực hiện thao tác. Token và quyền sở hữu vẫn được backend kiểm tra.

## Các màn hình

**Tìm địa chỉ tự do:** gõ tên đường, số nhà, trường học, bệnh viện hoặc địa điểm vào ô **Điểm đón / Điểm đến**. Sau khoảng 0,9 giây, ứng dụng tìm gợi ý trực tuyến qua Photon/OpenStreetMap. Chọn đúng kết quả để xác nhận vị trí; có thể dùng phím lên/xuống và Enter. Nên thêm tên quận/thành phố khi tên địa điểm có nhiều kết quả. Địa điểm chưa chọn không được dùng để đặt xe, tránh gửi nhầm tọa độ của lần chọn trước.

Danh mục có sẵn có hơn 40 địa điểm ở TP.HCM, Hà Nội, Đà Nẵng và một số thành phố khác, tìm được cả khi gõ không dấu. Các tọa độ trong danh mục là vị trí tham khảo. Có thể dán `vĩ độ,kinh độ` hoặc chọn **Nhập tọa độ** khi mạng không hoạt động. **Chọn trên bản đồ** cần tile OpenStreetMap đã tải xong, không cần cấu hình key.

Tìm trực tuyến gửi từ khóa và tọa độ ưu tiên khu vực đến nhà cung cấp Photon; không gửi token đăng nhập hoặc thông tin tài khoản. Kết quả phụ thuộc dữ liệu OpenStreetMap: không bảo đảm mọi số nhà/tên địa điểm đều có. Endpoint `/api/places/search` có timeout 4 giây, cache 15 phút (tối đa 256 truy vấn), giới hạn tối đa 1 truy vấn mới mỗi giây và không log nội dung địa chỉ. Đọc API/điều kiện máy chủ demo tại [Photon](https://github.com/komoot/photon) và [API reference](https://github.com/komoot/photon/blob/master/docs/api-v1.md). Dùng biến `GEOCODER_URL` nếu tự triển khai Photon hoặc chuyển sang nhà cung cấp tương thích.

| Màn hình | Thao tác |
|---|---|
| Đăng nhập / tạo tài khoản | Chọn passenger hoặc driver khi đăng ký; hiện/ẩn mật khẩu; báo lỗi nhập liệu/xác thực |
| Hành khách | Tìm địa chỉ, nhập tọa độ hoặc chọn trên OpenStreetMap; ước tính giá; tạo/hủy chuyến |
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

Map và marker dùng Leaflet cùng dữ liệu đường phố OpenStreetMap thật. Chọn/kéo ghim bị khóa khi có chuyến đang chạy; polling không tự căn lại bản đồ nếu tọa độ không đổi. Không tự vẽ tuyến đường hoặc ETA; giá vẫn theo khoảng cách Haversine. Đã kiểm chứng tile/click/drag thật bằng Edge, không chỉ dùng SDK doubles.

## Kiểm chứng

```powershell
python tests/test_web.py
python -m unittest tests.test_geocoding -v
node --check src/web/app.js
```

Kiểm thử tùy chọn bằng trình duyệt thật:

```powershell
npm install --prefix runtime/browser-qa playwright --no-save --no-package-lock
python scripts/start.py
# Terminal khác
node scripts/browser_qa.cjs
# Kiểm tra tìm địa chỉ thật, fallback offline và chọn bàn phím
$env:APP_URL = 'http://127.0.0.1:8080'
node scripts/address_qa.cjs
```

Script dùng Edge đã cài trên Windows; có thể đặt `BROWSER_PATH` cho Chrome/Edge khác. Không cần tải browser hoặc thêm dependency cho ứng dụng. Kết quả lưu `docs/browser-results.json`; ảnh desktop/tài xế/mobile tại `docs/ui-*.png`. Backend 24 bài, web proxy 6 bài và browser checks được báo cáo riêng.
