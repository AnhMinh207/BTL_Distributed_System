"""Generate editable Vietnamese report/slides HTML from actual test results.

No external dependency. Export the HTML using scripts/export_pdf.py or browser Print.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


def esc(value):
    return html.escape(str(value))


def p(text):
    return '<p>' + text + '</p>'


def bullets(*items):
    return '<ul>' + ''.join('<li>' + item + '</li>' for item in items) + '</ul>'


def table(headers, rows):
    return '<table><thead><tr>' + ''.join('<th>' + esc(x) + '</th>' for x in headers) + \
        '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + esc(x) + '</td>' for x in row) + '</tr>'
                                        for row in rows) + '</tbody></table>'


def code(text):
    return '<pre>' + esc(text) + '</pre>'


def document(pages, slides=False):
    size = '297mm 167mm' if slides else 'A4'
    height = '137mm' if slides else '265mm'
    css = '''
      * {box-sizing:border-box} body {margin:0;color:#142033;font-family:Arial,"Segoe UI",sans-serif;
      font-size:11pt;line-height:1.55} h1 {font-size:24pt;line-height:1.2;color:#104e64;margin:12mm 0 8mm}
      h2 {font-size:14pt;color:#17657a;margin:6mm 0 3mm} p {margin:3mm 0;text-align:justify}
      ul {padding-left:6mm} li {margin:3mm 0} table {width:100%;border-collapse:collapse;font-size:9.5pt;
      margin:5mm 0} th,td {padding:2.5mm;border:1px solid #b6cbd2;text-align:left;vertical-align:top}
      th {background:#e7f2f4} pre {white-space:pre-wrap;overflow-wrap:anywhere;font-size:9pt;
      line-height:1.45;background:#edf3f6;padding:4mm} .page {position:relative;break-after:page;
      padding:0 0 12mm} .page:last-child {break-after:auto} .eyebrow {font-size:9pt;color:#56717a;
      border-bottom:1px solid #bdd2da;padding-bottom:3mm;letter-spacing:1px}
      footer {position:absolute;bottom:0;width:100%;border-top:1px solid #bdd2da;padding-top:2mm;
      font-size:8pt;color:#56717a;display:flex;justify-content:space-between}
      .callout {padding:4mm;background:#e7f2f4;border-left:3px solid #17657a}
      .cover {padding-top:25mm} .cover h1 {font-size:32pt} a {color:#104e64;overflow-wrap:anywhere}
      .diagram {text-align:center;background:#edf3f6;padding:6mm;font-size:13pt;line-height:1.8}
    '''
    if slides:
        css += 'body{font-size:17pt}h1{font-size:28pt;margin:5mm 0}table{font-size:13pt}li{margin:4mm 0}pre{font-size:12pt}'
    css += f'@page{{size:{size};margin:14mm}}.page{{height:{height}}}'
    output = '<!doctype html><html lang="vi"><meta charset="utf-8"><title>DS03 — Báo cáo</title><style>' + css + '</style><body>'
    for i, (title, content) in enumerate(pages, 1):
        output += '<section class="page"><div class="eyebrow">DISTRIBUTED SYSTEMS · DS03 · RIDE HAILING</div>'
        output += '<h1>' + title + '</h1>' + content
        output += f'<footer><span>DS03 · Prototype học phần · 03/11/2026</span><span>{i} / {len(pages)}</span></footer></section>'
    return output + '</body></html>'


def main():
    DOCS.mkdir(exist_ok=True)
    results = json.loads((DOCS / 'test-results.json').read_text(encoding='utf-8'))
    perf = json.loads((DOCS / 'performance.json').read_text(encoding='utf-8'))
    team = (DOCS / 'team.md').read_text(encoding='utf-8')
    docker_file = DOCS / 'docker-results.json'
    docker_result = json.loads(docker_file.read_text(encoding='utf-8')) if docker_file.exists() else {'tests': []}
    docker_passed = sum(t['status'] == 'passed' for t in docker_result['tests'])
    docker_note = (f'Docker Compose đã build và chạy 7 container; {docker_passed}/8 kịch bản HTTP chọn lọc đạt, '
                   'gồm đặt xe, tranh tài xế, kill/restart Payment và Broker. Kết quả tại docs/docker-results.json.'
                   if docker_passed == 8 else 'Docker runtime chưa được kiểm chứng đủ 8 kịch bản chọn lọc.')
    web_docker_file = DOCS / 'docker-web-results.json'
    if web_docker_file.exists():
        web_docker = json.loads(web_docker_file.read_text(encoding='utf-8'))
        docker_note = (f'Bản web đã chạy 8 container healthy và {web_docker["browser_checks_passed"]} kiểm tra Edge thật. '
                       f'Bộ backend trước đó đạt {docker_passed}/8 ca Docker chọn lọc, gồm kill/restart Payment và Broker. '
                       'Nguồn: docs/docker-web-results.json và docs/docker-results.json.')
    def team_value(label):
        prefix = '- ' + label + ': '
        return esc(next((line[len(prefix):] for line in team.splitlines() if line.startswith(prefix)), '[điền]'))
    passed = sum(r['status'] == 'passed' for r in results['results'])
    pages = []
    add = lambda title, body: pages.append((title, body))
    add('BÁO CÁO BÀI TẬP LỚN', '<div class="cover">' +
        p('<strong>Học phần: Distributed Systems</strong>') +
        '<h1>DS03<br>Hệ thống gọi xe<br>Microservices</h1>' +
        p('Mô phỏng Grab/Uber · REST · Message Queue · Saga · Eventual Consistency') +
        p(f'Nhóm: {team_value("Tên nhóm")} · Lớp: {team_value("Lớp")}<br>Giảng viên: {team_value("Giảng viên")}') +
        p('Thành viên và MSSV: hoàn thiện theo trang 2 và docs/team.md.') +
        p('Ngày tạo bản triển khai: 03/11/2026 · Nguồn yêu cầu: COURSE PROJECT SPECIFICATION.pdf') +
        '<div class="callout">Bản kỹ thuật có kết quả chạy thực. Cần hoàn thiện thông tin nhóm, bằng chứng đóng góp và chạy lại trên máy nhóm trước nộp.</div></div>')
    add('1. Thông tin nhóm và phân công',
        p('Đề quy định nhóm tối đa 3 thành viên, mỗi người phụ trách phần việc cụ thể và có bằng chứng trên GitHub. Chưa có thông tin cá nhân trong yêu cầu nên báo cáo giữ các trường trống có chủ đích; bảng dưới là đề xuất để nhóm điều chỉnh, không xác nhận đóng góp đã xảy ra.') +
        table(['Thành viên / MSSV', 'Phần việc', 'Bằng chứng cần có'], [
            ('[Người 1] / [MSSV 1]', 'Identity, Driver, REST, bảo mật', 'Commit/PR thật; test S01–S03'),
            ('[Người 2] / [MSSV 2]', 'Trip, Matching, Saga, đồng thời', 'Commit/PR thật; test C01–C03, R06'),
            ('[Người 3, nếu có] / [MSSV 3]', 'Broker, Payment, Notification, triển khai', 'Commit/PR thật; R01–R05, hiệu năng')]) +
        p('Thông tin nguồn hiện có trong docs/team.md:') + code(team[:2400]) +
        p('Các thành viên cần hiểu toàn bộ kiến trúc, tham gia demo và giải thích cơ chế mình triển khai. Nếu nhóm có ít hơn 3 người, phân công lại đủ phạm vi. Không tạo lịch sử Git hay danh tính giả để thay bằng chứng thực tế.'))
    add('2. Tóm tắt và cấu trúc báo cáo',
        p('Dự án xây dựng prototype đặt xe từ lúc hành khách gửi yêu cầu đến khi tài xế hoàn tất và thanh toán mô phỏng. Hệ thống gồm Identity, Driver, Trip, Matching, Payment, Notification và một broker riêng. Mỗi dịch vụ chạy trong tiến trình độc lập, sở hữu SQLite riêng và giao tiếp qua mạng; không truy vấn chéo dữ liệu.') +
        p('Luồng đồng bộ dùng REST để đăng nhập, thao tác chuyến và giữ tài xế. Luồng bất đồng bộ dùng hàng đợi có lưu bền, lease, ACK, retry và dead-letter. Saga phối hợp các giao dịch cục bộ; hủy, quá hạn hoặc thanh toán thất bại kích hoạt giải phóng tài xế. Outbox và inbox giảm rủi ro mất sự kiện và lặp tác dụng sau crash.') +
        p(f'Bộ đánh giá chạy {results["tests"]} bài qua HTTP thật giữa 7 tiến trình: {passed} đạt, {results["failures"]} thất bại và {results["errors"]} lỗi. Mất kết nối được tái hiện bằng kill tiến trình, không thay bằng biến trạng thái giả. ' + docker_note) +
        table(['Phạm vi', 'Trang'], [('Bài toán, phân tích, kiến trúc', '4–8'), ('API, MQ, discovery', '9–11'),
             ('Đồng thời, nhất quán, Saga', '12–14'), ('Lỗi, bảo mật, triển khai', '15–18'),
             ('Kiểm thử, hiệu năng', '19–21'), ('Giới hạn, kết luận, tham khảo, phụ lục', '22–24')]) +
        p('Đây là sản phẩm học phần; chưa phải dịch vụ gọi xe vận hành công khai. Có web tiếng Việt cho hai vai trò và CLI. Sơ đồ vị trí SVG, tọa độ và thanh toán được mô phỏng; chưa có bản đồ đường bộ hoặc tiền thật.'))
    add('3. Bài toán và yêu cầu',
        p('Hành khách muốn tạo chuyến với điểm đón và điểm đến. Tài xế công bố trạng thái cùng vị trí mô phỏng, nhận đề nghị rồi chấp nhận hoặc từ chối. Sau khi chấp nhận, tài xế bắt đầu và hoàn thành chuyến. Hệ thống tính giá phía server, tạo thanh toán mô phỏng và thông báo cho các bên liên quan.') +
        p('Rủi ro trung tâm là hai yêu cầu gần đồng thời tranh cùng một tài xế, cùng một yêu cầu được gửi lại do timeout, hoặc một bước đã commit nhưng bước tiếp theo chưa nhận sự kiện. Trạng thái không thể chỉ đặt trong RAM hoặc database chung vì các dịch vụ cần chạy và phục hồi độc lập.') +
        table(['Nhóm yêu cầu', 'Tiêu chí áp dụng'], [('Phân tán', '≥3 process; DS03 ≥4 business service; dữ liệu riêng'),
              ('Chức năng', 'Tài khoản, tài xế, booking, matching, vòng đời, fare, payment, notification'),
              ('Giao tiếp', 'REST/gRPC và MQ bất đồng bộ; event ID; correlation ID'),
              ('Tin cậy', 'Retry, dedup, DLQ/error storage; Saga/compensation'),
              ('Kiểm chứng', '≥8 chức năng; ≥2 đồng thời; ≥2 lỗi; ≥2 bảo mật; ≥1 hiệu năng'),
              ('Bàn giao', 'Repo đúng cấu trúc; báo cáo PDF; hướng dẫn tái triển khai; đóng góp thật')]) +
        p('Không triển khai các yêu cầu đặc thù P2P/WAN của DS01, chunk của DS02 hay CRDT của DS04. Ma trận đầy đủ nối từng tiêu chí với file và test ở docs/requirements-matrix.md. Các yêu cầu chung mục 4, 9–13 vẫn được giữ.'))
    add('4. Những vấn đề hệ phân tán',
        bullets('<strong>Lỗi từng phần:</strong> Trip có thể khỏe trong khi Payment hoặc Broker đã dừng. Thành công HTTP của complete chỉ xác nhận trạng thái cục bộ awaiting_payment, chưa xác nhận toàn bộ Saga hoàn tất.',
                '<strong>Không biết chắc kết quả sau timeout:</strong> Driver có thể đã giữ xe dù Matching không nhận response. Retry phải theo trip_id để trả lại cùng reservation, tránh giữ thêm tài xế.',
                '<strong>Giao lại và đảo thứ tự:</strong> ACK có thể mất; cancellation có thể đến trước reserve. ID sự kiện, inbox và reservation tombstone là các lớp bảo vệ khác nhau.',
                '<strong>Tranh chấp tài nguyên:</strong> Hai process/người dùng yêu cầu đồng thời cần quyết định duy nhất tại nơi sở hữu tài nguyên Driver. Trạng thái cache hoặc kết quả đọc trước đó không đủ để ngăn double booking.',
                '<strong>Nhất quán liên dịch vụ:</strong> Một commit không bao phủ tất cả DB. Hệ thống chọn eventual consistency và nêu rõ trạng thái trung gian thay vì che giấu bằng kết quả giả đồng bộ.') +
        p('Mô hình lỗi: tiến trình crash-stop rồi restart, kết nối bị từ chối/timeout, ACK không đến và sự kiện lặp/đến muộn. Database còn nguyên trên đĩa sau crash. Không giả định broker Byzantine, hỏng đĩa hoặc partition vô hạn tự phục hồi. Với lỗi kéo dài, DLQ bảo toàn bằng chứng và cần người vận hành xử lý.') +
        p('Khi dependency không hoạt động, hệ thống ưu tiên giữ các invariant và dữ liệu đã commit. Nó có thể tạm thời không cấp chuyến mới hoặc giữ driver busy khi chờ payment, chấp nhận giảm availability thay vì gán một tài xế cho hai chuyến.'))
    add('5. Phân tích và lựa chọn giải pháp',
        table(['Lựa chọn', 'Áp dụng và lý do', 'Đánh đổi'], [
            ('Python chuẩn + HTTP JSON', 'Không phụ thuộc pip; dễ chạy 7 process; dễ quan sát giao thức', 'http.server chỉ phù hợp prototype'),
            ('SQLite riêng/service', 'Giao dịch ACID cục bộ, unique constraints, persistence', 'Một writer mỗi DB; chưa replication'),
            ('Broker tự triển khai', 'Kiểm chứng enqueue/lease/ACK/DLQ rõ trong code', 'Chưa có HA và vận hành như RabbitMQ'),
            ('Saga choreography', 'Các service phản ứng qua event, không transaction chung', 'Theo dõi luồng khó hơn; cần correlation ID'),
            ('Outbox + inbox', 'Đóng khoảng trống commit DB/publish và process/ACK', 'Cần polling; lưu log tăng theo thời gian'),
            ('Web + CLI', 'Web hai vai trò, sơ đồ tọa độ, timeline, demo thật; CLI để vận hành', 'Sơ đồ minh họa, chưa bản đồ đường bộ/ETA')]) +
        p('Không sử dụng một sản phẩm gọi xe có sẵn rồi đổi giao diện. Các cơ chế cốt lõi được hiện thực trực tiếp: reserve nguyên tử, version guard, outbox/inbox, queue receipt/lease, retry, DLQ, redrive, compensation và tombstone. Thư viện chuẩn cung cấp HTTP, SQLite, hash, tiến trình và kiểm thử.') +
        p('Một broker chuyên dụng là hướng nâng cấp hợp lý, nhưng không tự động thay thế idempotency hay Saga. Dù dùng broker nào, nếu consumer commit rồi crash trước ACK, việc giao lại vẫn phải được xử lý bằng khóa nghiệp vụ/inbox. Thiết kế giữ rõ ranh giới này.'))
    add('6. Kiến trúc tổng thể',
        '<div class="diagram">Web passenger / driver :8080 · CLI<br>↓ Public API Proxy + REST + bearer token<br>Identity · Driver · Trip · Payment · Notification<br><br>Trip outbox → Durable Broker → Matching<br>Matching → REST reserve → Driver<br>Matching outbox → Broker → Trip<br>Trip completed → Broker → Payment<br>Payment result → Broker → Trip + Driver + Notification</div>' +
        p('Mỗi khối là một tiến trình và một database. Matching không đọc bảng Driver: nó gửi POST /internal/reserve và nhận driver_id. Trip không đọc Payment: nó nhận payment.succeeded hoặc payment.failed qua queue. Notification không truy vấn Trip để tạo thông báo: dữ liệu cần thiết được mang trong event.') +
        p('Producer ghi business state và outbox trong một transaction. Publisher đưa envelope tới Broker, Broker commit rồi trả ACK. Consumer chủ động claim, xử lý business state và inbox, commit rồi ACK delivery. Broker không chạy logic matching, tính fare hay thay đổi lifecycle.') +
        p('Web proxy chỉ forward API công khai qua allowlist, không đọc DB hoặc mở API nội bộ. Sáu dịch vụ nghiệp vụ vượt tối thiểu bốn; web và broker không được tính. Compose có tám container, bảy backend có volume riêng. Frontend polling trạng thái mỗi 2 giây; backend quyết định toàn bộ kết quả nghiệp vụ.'))
    add('7. Thành phần và thiết kế dữ liệu',
        table(['Service', 'Bảng chính', 'Khóa/ràng buộc'], [
            ('Identity', 'users', 'id PK; username UNIQUE; salt + password_hash'),
            ('Driver', 'drivers, reservations', 'driver.id PK; active_trip UNIQUE; reservation.trip_id PK'),
            ('Trip', 'trips, requests', 'trip.id PK; (passenger,key) PK; unique active passenger'),
            ('Matching', 'matches', 'trip_id PK; lưu driver_id và matched/failed'),
            ('Payment', 'payments', 'trip_id PK; amount, paid/declined, hai user liên quan'),
            ('Notification', 'notifications', '(event_id,user_id) PK; topic, trip_id, timestamp'),
            ('Broker', 'events, deliveries', 'event.id PK; (queue,event_id) PK; state/attempts/lease')]) +
        p('Mỗi business DB có inbox(id,processed_at) và outbox(id,envelope,published). Các bảng này thuộc cùng chủ dữ liệu nên được cập nhật cùng transaction với bảng nghiệp vụ. Chúng không phải shared file giao tiếp liên dịch vụ.') +
        p('Database khởi tạo WAL để reader có thể tiếp tục đọc snapshot trong lúc writer ghi. BEGIN IMMEDIATE lấy quyền ghi trước khi chọn/cập nhật tài nguyên. busy_timeout giúp writer cạnh tranh chờ hữu hạn, nhưng không tạo khóa phân tán giữa các database khác nhau.') +
        p('Kho lưu trữ mặc định ở runtime/<service>/state.db; Compose ở volume riêng dưới /data/<service>. Giữ volume khi tái triển khai để phục hồi. Xóa database sẽ làm mất lịch sử, inbox và dedup; đó không phải thao tác restart và không nằm trong mô hình kiểm thử phục hồi.'))
    add('8. Thiết kế REST và quyền truy cập',
        table(['Đường dẫn', 'Quyền / ý nghĩa'], [('POST Identity /register, /login', 'Public; role passenger/driver, trả token'),
            ('POST/GET Driver /drivers/me', 'Driver; cập nhật/đọc profile của mình'),
            ('POST Trip /trips', 'Passenger; pickup, destination, mode; Idempotency-Key'),
            ('GET Trip /trips và /trips/{id}', 'Chỉ passenger sở hữu hoặc driver được gán'),
            ('POST /trips/{id}/{action}', 'Role/owner, trạng thái và version đều phải hợp lệ'),
            ('GET Payment /payments', 'Chỉ ledger liên quan user'),
            ('GET Notification /notifications', 'Chỉ hộp thư user'),
            ('POST Driver /internal/reserve', 'Service key; một giao dịch chọn và giữ driver')]) +
        p('Input JSON có giới hạn 64 KiB. Tọa độ là mảng hai số hữu hạn trong miền latitude/longitude; bool không được chấp nhận như số. Username chỉ gồm ký tự được phép. Không tin các trường passenger_id, driver_id hoặc fare do client muốn tự khai báo.') +
        p('HTTP 400 thể hiện dữ liệu sai, 401 thiếu/sai token, 403 sai quyền, 404 không tồn tại, 409 xung đột version/state/key và 413 quá kích thước. Dependency không truy cập được được ánh xạ 503. HTTP 200 ở API complete trả awaiting_payment có ý nghĩa khác completed.') +
        code('POST /trips/<id>/accept\nAuthorization: Bearer <driver-token>\nX-Correlation-ID: <optional-id>\n\n{"version": 2}') +
        p('Nếu mất response, client đọc lại chuyến. Không tự gửi lệnh accept/start/complete mù với version mới vì có thể thay đổi ý định người dùng. API chi tiết và schema thông báo lỗi ở docs/architecture.md.'))
    add('9. Message queue và envelope',
        code('{\n  "id": "UUID-event",\n  "topic": "trip.requested",\n  "producer": "trip",\n  "timestamp": 1793680000.0,\n  "correlation_id": "UUID-saga",\n  "payload": {"trip_id": "UUID-trip", "passenger_id": "UUID-user",\n              "pickup": [10.7769,106.7009], "version": 1}\n}') +
        table(['Topic', 'Consumer'], [('trip.requested', 'Matching, Notification'),
            ('driver.reserved / matching.failed', 'Trip, Notification'),
            ('trip.accepted / trip.started', 'Notification'),
            ('trip.completed', 'Payment, Notification'),
            ('trip.cancelled', 'Driver, Notification'),
            ('payment.succeeded / payment.failed', 'Trip, Driver, Notification')]) +
        p('Broker lưu envelope một lần và tạo một delivery cho từng queue subscriber trong cùng transaction. Publish cùng ID/nội dung trả duplicate=true; cùng ID khác nội dung bị từ chối. Consumer claim nhận event và receipt duy nhất; chỉ receipt còn lease mới ACK/NACK được.') +
        p('Producer không gọi trực tiếp consumer để hoàn tất nghiệp vụ. Khi Payment dừng, trip.completed vẫn enqueue được và được xử lý sau restart. HTTP là transport để publish/pull, còn ngữ nghĩa là durable asynchronous message queue. Thứ tự retry không được cam kết FIFO tuyệt đối; correctness dựa vào dedup và guard trạng thái.'))
    add('10. Định danh, discovery và thời gian',
        p('Service có tên ổn định và cổng mặc định 8100–8106. User, trip, event và receipt dùng UUID; Correlation ID được giữ trong mọi event của một Saga. Event ID dùng chống trùng; trip_id dùng idempotency nghiệp vụ; correlation_id chỉ để truy vết và không thay thế hai khóa trên.') +
        table(['Cơ chế', 'Cách triển khai'], [('Local discovery', 'BROKER_URL, DRIVER_URL và các biến SERVICE_URL'),
              ('Compose discovery', 'DNS broker, driver… trên network ds03'),
              ('Service health', 'GET /health kiểm DB riêng; HTTP timeout phát hiện dependency fail'),
              ('Driver presence', 'updated; chỉ available trong 300 giây gần nhất mới là candidate'),
              ('Delivery lease', 'Broker tính deadline; mặc định 3 giây'),
              ('Saga deadlines', 'requested 60s, offered 120s mặc định; cấu hình qua env')]) +
        p('Driver heartbeat được mô phỏng bằng gửi lại POST /drivers/me với vị trí hiện tại. Khi có chuyến, status busy cập nhật tọa độ mà không xóa active_trip. Khi offline hoặc quá thời gian hiện diện, driver không được chọn cho yêu cầu mới.') +
        p('Log timestamp ở UTC để so sánh giữa node. Sắp xếp notification theo timestamp chỉ phục vụ hiển thị, không quyết định tính đúng của transaction. Chưa dùng Lamport/vector clock vì dữ liệu có một service sở hữu và concurrency được giải tại service đó. Với đa máy, cần đồng bộ thời gian; báo cáo không giả định global clock hoàn hảo.') +
        p('Discovery qua cấu hình/DNS thỏa phạm vi prototype; chưa có registry động, leader election hoặc failover endpoint. Khi thay URL, phải tái khởi động service nhận cấu hình mới.'))
    add('11. Kiểm soát đồng thời',
        p('Tình huống chính: hai hành khách gửi yêu cầu gần đồng thời, Matching xử lý hai event cùng có một tài xế gần. Việc chọn tài xế và đánh dấu busy phải là một giao dịch trong Driver, không thể thực hiện bằng một GET danh sách rồi một PUT giữ riêng biệt.') +
        code('BEGIN IMMEDIATE;\nSELECT ... FROM drivers\n WHERE status=\'available\' AND active_trip IS NULL;\n-- Lọc presence, khoảng cách và chọn gần nhất\nUPDATE drivers SET status=\'busy\', active_trip=:trip\n WHERE id=:driver AND active_trip IS NULL;\nINSERT INTO reservations(trip_id,driver_id,state) VALUES(...);\nCOMMIT;') +
        p('Writer thứ hai chờ transaction đầu hoàn thành rồi nhìn trạng thái busy, do đó không thể chọn lại cùng driver. Nếu không còn candidate, reservation unavailable được lưu theo trip và Matching phát matching.failed. Với chỉ một driver, kết quả đúng là một chuyến offered và một chuyến cancelled.') +
        p('Tranh chấp thứ hai: accept và reject cùng version. Trip tuần tự hóa writer, kiểm version hiện tại trước chuyển state. Chỉ một lệnh thắng; lệnh còn lại trả 409 và version chỉ tăng một lần. Tranh chấp thứ ba: nhiều POST booking cùng Idempotency-Key từ một passenger tạo đúng một trip.') +
        p('Các invariant được kiểm chứng qua API, không bằng việc test đọc trực tiếp database rồi tự sửa trạng thái. C01, C02, C03 dùng ThreadPool để tạo concurrency từ client. SQLite chỉ khóa trong một service; không có giả định khóa đó bao phủ các service khác.'))
    add('12. Nhất quán và idempotency',
        p('Mô hình nhất quán là ACID cục bộ và eventual consistency giữa các service. Driver có thể đã busy trước khi Trip chuyển offered; Payment có thể đã ghi paid trước khi Trip nhận payment.succeeded. Các trạng thái trung gian được giữ và có thể quan sát; không gán nghĩa atomic toàn hệ thống cho các response cục bộ.') +
        table(['Lớp', 'Cơ chế chống lặp'], [('Client → Trip', '(passenger_id,key) và fingerprint payload chuẩn hóa; khác nội dung trả 409'),
              ('Publisher → Broker', 'event ID UNIQUE và so envelope cùng ID'),
              ('Broker → Consumer', 'inbox ID được commit cùng tác dụng nghiệp vụ'),
              ('Matching → Driver', 'reservation.trip_id PK; retry trả cùng quyết định'),
              ('Payment', 'payment.trip_id PK, dù nhận event ID khác'),
              ('Lifecycle commands', 'version + state precondition; caller đọc lại khi 409')]) +
        p('Inbox chỉ được ghi sau khi handler thành công trong transaction. ACK chỉ được gửi sau commit. Nếu consumer chết sau commit trước ACK, lần giao lại tìm thấy inbox và ACK mà không áp dụng lại. Broker retry là at-least-once trước khi đạt giới hạn, sau đó chuyển DLQ; hệ thống không tuyên bố exactly-once delivery.') +
        p('Đảo thứ tự được xử lý theo ngữ nghĩa: release tạo tombstone ngay cả nếu chưa có reserve; terminal trip không quay về offered; payment đến sai giai đoạn bị retry/error thay vì nhảy state tùy tiện. Notification lưu lịch sử sự kiện, không dùng last-write-wins để ghi đè nguồn sự thật của Trip.'))
    add('13. Saga và hành động bù',
        '<div class="diagram">requested → reserve driver → offered<br>→ accepted → in_progress → awaiting_payment<br>→ paid: completed + release driver<br>→ declined: payment_failed + release driver</div>' +
        p('Mỗi mũi tên thuộc một transaction cục bộ hoặc sự kiện mạng. Saga sử dụng choreography: Trip, Matching, Driver và Payment phối hợp bằng event/REST idempotent, không có transaction chung giữa các DB. Trip lưu trạng thái tổng quan cùng deadline để giám sát các giai đoạn đầu.') +
        table(['Nguyên nhân', 'Hành động bù', 'Trạng thái cuối'], [('Không có driver', 'trip.cancelled; tombstone/release an toàn', 'cancelled'),
              ('Driver reject / passenger cancel', 'Release reservation theo trip_id', 'cancelled'),
              ('requested/offered quá hạn', 'Cancel + sự kiện release, kể cả match đến muộn', 'cancelled'),
              ('Payment decline', 'Giữ ledger declined; release driver', 'payment_failed'),
              ('Payment offline', 'Không tự hủy; giữ queue và busy, xử lý sau restart', 'awaiting_payment → terminal')]) +
        p('Nếu Matching đã giữ driver nhưng crash trước phát kết quả, event requested được giao lại và reserve cùng trip_id không chọn thêm driver. Nếu Trip đã cancelled, tombstone hoặc compensation đến muộn sẽ giải phóng reservation. R04 và R06 kiểm chứng cả thứ tự release trước reserve và deadline trước matching.') +
        p('Không thể hoàn tác quãng đường đã chạy bằng một database rollback. Với payment decline, prototype chỉ kết thúc trạng thái mô phỏng và giải phóng tài nguyên; chưa có mô hình công nợ, thu hồi tiền hoặc refund thực tế. Đây là giới hạn nghiệp vụ được công bố.'))
    add('14. Chịu lỗi và phục hồi',
        table(['Điểm lỗi', 'Dữ liệu còn lại', 'Cách phục hồi'], [('Producer crash trước publish', 'Business state + outbox chưa published', 'Restart publisher gửi tiếp'),
              ('Broker commit, response mất', 'Event và deliveries đã lưu', 'Publish lại ID; broker dedup'),
              ('Consumer crash trước commit', 'Delivery inflight, chưa có inbox', 'Lease hết hạn; giao lại'),
              ('Consumer commit, ACK mất', 'Business state + inbox đã lưu', 'Giao lại; inbox ngăn lặp'),
              ('Handler lỗi nhiều lần', 'attempts, error và event còn lưu', 'Backoff; DLQ; operator redrive'),
              ('Broker process crash', 'SQLite persistent trên đĩa', 'Restart; lease/queue tiếp tục')]) +
        p('Retry NACK sử dụng backoff tăng theo số attempt, tối đa 8 giây. MAX_ATTEMPTS mặc định 5; demo/test dùng 3 để quan sát nhanh. Claim làm tăng attempt; lease hết hạn ở lần claim sau chuyển pending hoặc dead. Receipt mới khác receipt cũ để ACK trễ không xác nhận nhầm delivery mới.') +
        p('Outbox không tự bỏ event khi broker dừng; publisher thử lại ở khoảng cách được giới hạn. Việc retry không chặn commit yêu cầu mới của Trip. Deadline requested/offered được kiểm tra cục bộ kể cả khi broker mất kết nối; compensation được giữ trong outbox để gửi sau.') +
        p('DLQ không phải tự động thành công. Người vận hành cần đọc lỗi, phục hồi dependency hoặc sửa dữ liệu/code rồi redrive. Với chuyến đã terminal, event được xử lý idempotent và không hồi sinh chuyến. Không có bảo đảm eventual completion nếu operator bỏ mặc DLQ, partition vô hạn hoặc đĩa bị mất.'))
    add('15. Bảo mật',
        bullets('<strong>Authentication:</strong> Identity lưu PBKDF2-HMAC-SHA256 với salt ngẫu nhiên từng user, 200.000 vòng. Token có HMAC-SHA256, subject, role và hạn exp; mặc định sống 3.600 giây.',
                '<strong>Authorization:</strong> Driver chỉ cập nhật profile của mình; Passenger chỉ tạo chuyến cho mình; chỉ driver được gán mới accept/start/complete; chỉ user liên quan đọc trip/payment/notification.',
                '<strong>Service authentication:</strong> Broker và /internal/reserve yêu cầu X-Service-Key. Token user không cho quyền vận hành queue hoặc tự giữ driver.',
                '<strong>Input:</strong> Giới hạn 64 KiB; JSON object; username, password, role, tọa độ hữu hạn và version integer được kiểm tra. SQL tham số hóa; client không quyết định fare hay owner.',
                '<strong>Secrets và logs:</strong> .env được ignore, .env.example không chứa secret; configure tạo ngẫu nhiên. Log không chứa password/token/body. Health chỉ lộ tên service và status.') +
        p('Mô hình tin cậy nội bộ còn đơn giản: các service dùng chung key, chưa có mTLS, ACL theo service hay secret rotation. Token chưa có revoke, đăng nhập chưa rate-limit. Hash có salt bảo vệ lưu trữ nhưng không giải quyết mọi rủi ro chiếm tài khoản.') +
        p('HTTP localhost/Compose là cấu hình demo. Trước khi mở Internet phải bổ sung TLS, reverse proxy, giới hạn tốc độ và nguồn kết nối. Python http.server được dùng để dễ kiểm chứng, chưa là application server sản xuất. Các hạn chế được ghi để tránh hiểu nhầm mức an toàn mà kiểm thử hiện tại chứng minh.'))
    add('16. Hiện thực và cấu trúc mã',
        table(['Thư mục/file', 'Nội dung'], [('src/common.py', 'HTTP adapter, config, auth, DB transaction, publisher/consumer worker'),
              ('src/{identity,driver,trip,matching,payment,notification}.py', 'Sáu domain service, mỗi service chỉ DB riêng'),
              ('src/broker.py', 'Durable event/delivery queue, lease, retry, dead letter, redrive'),
              ('src/main.py', 'Entrypoint một service, kiểm secret tối thiểu'),
              ('src/web/ và scripts/web.py', 'Web tiếng Việt và public API proxy; không mở internal/broker API'),
              ('scripts/', 'Configure, start web/cluster, CLI, tests, demo, tạo/xuất tài liệu'),
              ('tests/test_system.py', 'Black-box integration trên network, concurrency, kill/restart'),
              ('deploy/', 'Dockerfile non-root, Compose 8 container; 7 backend/volume riêng'),
              ('docs/', 'Thiết kế, ma trận yêu cầu, nhóm, số đo, PDF, demo, checklist')]) +
        p('Công thức fare dùng khoảng cách đường chim bay Haversine trên bán kính Trái Đất 6.371 km: 12.000 VND cơ bản + round(8.000 × km). Đây không phải lộ trình đường bộ hoặc bảng giá chính thức Grab/Uber. Driver được lọc trong bán kính 20 km, gần nhất thắng, UUID làm tie-break ổn định.') +
        p('Worker publisher và consumer chạy thread bên trong từng service. Đây là xử lý nội bộ; giao tiếp sang service khác vẫn qua HTTP. HTTP server tiếp nhận nhiều request song song; ghi dữ liệu được serialize tại DB sở hữu. Launcher tạo bảy tiến trình OS độc lập, không dùng thread để giả lập bảy microservice.') +
        p('Không cần cài package pip để chạy sản phẩm và test. Tài liệu HTML/PDF cũng có script riêng, không nằm trên đường xử lý nghiệp vụ. Mọi module chuẩn được liệt kê trong mã import và nguồn tham khảo cuối báo cáo.'))
    add('17. Cài đặt và tái triển khai',
        p('Môi trường xác nhận: Windows, Python 3.13, bảy process localhost. Mã dùng thư viện chuẩn, yêu cầu Python 3.11+. Cổng sản phẩm 8100–8106; test/demo 9100–9106. Tạo secret một lần, giữ .env ngoài repository.') +
        code('python scripts/start.py --open\n# Trình duyệt: http://127.0.0.1:8080\n# Chọn Chuẩn bị demo → Đặt xe → đổi sang Tài xế\n# Chấp nhận → Bắt đầu → Hoàn thành\n# Xem lịch sử, thanh toán, thông báo\n# CLI tùy chọn: python scripts/client.py status') +
        p('Docker Compose dùng DNS service, healthcheck, user không phải root và volume riêng. Host chỉ publish 127.0.0.1. Có thể start/stop riêng Payment để chứng minh xử lý độc lập. Tái triển khai giữ nguyên volume; không dùng down -v khi cần phục hồi dữ liệu.') +
        code('docker compose --env-file .env -f deploy/compose.yaml up --build -d\ndocker compose --env-file .env -f deploy/compose.yaml stop payment\ndocker compose --env-file .env -f deploy/compose.yaml start payment\ndocker compose --env-file .env -f deploy/compose.yaml down\n# Chạy lại up để tái triển khai, dữ liệu vẫn trong named volumes') +
        '<div class="callout">' + docker_note + ' Bộ 24 bài đầy đủ chạy bằng process Python; 8 ca Docker là tập con được xác nhận riêng, không gộp thành 32 bài khác nhau.</div>' +
        p('Backup/restore phải tôn trọng ranh giới dữ liệu từng service. Chưa có coordinated snapshot hoặc replication. Tái triển khai trên nhiều máy cần chỉnh SERVICE_URL/HOST, firewall và bảo vệ secret; chưa đo latency WAN.'))
    functional = [r for r in results['results'] if r['test'].startswith('test_F')]
    add('18. Kiểm thử chức năng',
        p('Bộ test tạo tài khoản, request và token qua API công khai, gọi service qua HTTP trên bảy process thực. Mỗi run có thư mục database/log riêng và random secret. Không dùng mock network để thay thế các luồng chính. Dữ liệu test được tách bằng vị trí cách xa nhau để driver của một tình huống không ảnh hưởng matching tình huống khác.') +
        table(['Test', 'Chức năng', 'Kết quả'], [(r['test'].split('_')[1], r['test'][9:].replace('_', ' '), r['status']) for r in functional]) +
        p('F03 kiểm cả full lifecycle, ledger paid, release tài xế và không cho tài xế tự chuyển available khi có chuyến. F06 kiểm notification của cả hai vai trò. F07 kiểm cùng key trả cùng trip và khác payload trả 409. F09 kiểm decline giữ ledger và Saga release. F11 kiểm broker dedup cùng envelope và reject event ID bị tái sử dụng khác nội dung.') +
        p('Chi tiết assertion nằm trong tests/test_system.py. Kết quả từng bài, thời gian và lỗi nếu có được ghi tự động vào docs/test-results.json; báo cáo này đọc từ file đó, không ghi tay PASS cho những tình huống chưa chạy.'))
    concurrent = [r for r in results['results'] if r['test'].startswith(('test_C', 'test_R'))]
    add('19. Đồng thời, lỗi và phục hồi',
        table(['Test', 'Tình huống', 'Kết quả'], [(r['test'].split('_')[1], r['test'][9:].replace('_', ' '), r['status']) for r in concurrent]) +
        p('C01 bắt buộc đúng một offered và một cancelled khi hai khách cùng tranh một tài xế; kiểm active_trip bằng API Driver. C02 đua accept/reject cùng version và chỉ chấp nhận một lệnh. C03 gửi tám request cùng key và kiểm chỉ có một trip ID.') +
        p('R01 kill Payment rồi complete, xác nhận awaiting_payment và queue pending, restart và chờ completed/available. R02 kill Broker, ghi booking vào outbox, restart và hoàn tất luồng. R03 kill Driver, chờ Matching đủ ba attempts vào DLQ, restart Driver, redrive và hoàn tất.') +
        p('R04 phát cancellation trước reserve, kiểm tombstone giữ driver available. R05 giữ một delivery inflight, restart Broker, đợi hết lease, claim lại bằng receipt mới và từ chối ACK receipt cũ. R06 giảm deadline ở Trip trong một tình huống, dừng Matching, đợi cancelled rồi khởi động Matching: chuyến không hồi sinh và driver được giải phóng.') +
        p('Các process được kill bằng API subprocess của runner; log ghi PID mới khi restart. Lỗi từng phần được tái hiện thực, nhưng chưa kiểm crash hệ điều hành, hỏng đĩa hoặc partition dài trên nhiều máy.'))
    security = [r for r in results['results'] if r['test'].startswith('test_S')]
    add('20. Bảo mật và đánh giá hiệu năng',
        table(['Test bảo mật', 'Kết quả'], [(r['test'][5:].replace('_', ' '), r['status']) for r in security]) +
        p('S01 kiểm token bắt buộc, ownership, role và service key. S02 kiểm tọa độ ngoài miền/bool, mật khẩu sai, role không hợp lệ và body quá 64 KiB. S03 kiểm sửa chữ ký token và gọi complete sai giai đoạn. Đây là kiểm chứng một số thuộc tính, không phải penetration test toàn diện.') +
        table(['Chỉ số thực đo Z01', 'Giá trị'], [('Phạm vi', perf['experiment']),
            ('Thành công', f'{perf["requests"]}/{perf["requests"]}; {perf["success_rate"]*100:.0f}%'),
            ('Thời lượng', f'{perf["duration_seconds"]} giây'),
            ('Throughput', f'{perf["throughput_rps"]} request/giây'),
            ('p50 / p95 / max', f'{perf["p50_ms"]} / {perf["p95_ms"]} / {perf["max_ms"]} ms'),
            ('Toàn bộ bộ test', f'{results["tests"]} bài; {passed} đạt; {results["duration_seconds"]} giây')]) +
        p('Đo bằng time.perf_counter ở client, bao gồm thiết lập HTTP connection, xác thực token, đọc DB và parse response. Có 10 worker và tổng 100 request GET /trips của một user; p50/p95 lấy từ danh sách latency đã sắp. Không có SLA đặt sẵn nên không biến số đo thành cam kết.') +
        p('Kết quả là một lần chạy localhost trên máy thực hiện, có hoạt động nền của các service. Không suy ra booking throughput, latency p95 WAN, số driver tối đa hay khả năng mở rộng đa máy. Chưa đo CPU/RAM/bandwidth; các chỉ số này là tùy chọn trong đề, không được bịa thêm.'))
    add('21. Hạn chế và hướng phát triển',
        bullets('<strong>Availability:</strong> Broker và mỗi service chỉ có một instance; persistence chưa thay thế replication. Cần broker cluster và database replication để chịu mất node/đĩa.',
                '<strong>Scalability:</strong> SQLite một writer/service, queue polling và HTTP connection mới cho mỗi call giới hạn throughput. Cần benchmark booking và cân nhắc PostgreSQL, connection pool, broker chuyên dụng.',
                '<strong>Nghiệp vụ:</strong> Chưa có đường đi thực, ETA, đánh giá tài xế, hủy khi đang chạy, tái matching sau reject hay công nợ/refund thực. Decline hiện chỉ đóng Saga mô phỏng.',
                '<strong>Bảo mật:</strong> Chưa TLS/mTLS, ACL từng service, token revoke, rate limit hoặc secret rotation. http.server chỉ phù hợp prototype trong phạm vi kiểm soát.',
                '<strong>Vận hành:</strong> DLQ redrive thủ công; chưa retention/compaction inbox/outbox/events; log và DB tăng theo thời gian. Cần dashboard queue age, lag, tỷ lệ lỗi và cảnh báo.',
                '<strong>Giao diện:</strong> Web responsive đã có đầy đủ vai trò, lịch sử/thanh toán/thông báo và demo. Sơ đồ SVG minh họa tọa độ; chưa bản đồ đường bộ, ETA hoặc mobile app native. Notification là hộp thư pull, chưa push/email/SMS.') +
        p('Ưu tiên phát triển: bổ sung TLS/rate-limit và ACL nội bộ; sau đó đo end-to-end booking/độ phục hồi nhiều máy; cuối cùng mới mở rộng thuật toán matching và trải nghiệm giao diện. Không dùng nhiều instance SQLite ghi chung file để tạo cảm giác đã scale ngang.') +
        p('Những yêu cầu bên ngoài mã nguồn vẫn còn phụ thuộc nhóm: đăng ký thông tin với giảng viên, commit từng thành viên, cấp quyền repository, tạo tag/release và tham gia demo/vấn đáp. Chúng được liệt kê rõ trong checklist bàn giao.'))
    add('22. Kết luận và tài liệu tham khảo',
        p(f'Prototype thể hiện sáu business service độc lập, REST và MQ, quyền sở hữu dữ liệu tách biệt, tranh chấp tài xế, Saga compensation và phục hồi process. Kết quả thực hiện có {passed}/{results["tests"]} bài đạt. Các kết luận giới hạn trong failure model và workload đã chạy; không khẳng định đạt HA hoặc sẵn sàng Internet.') +
        p('Nguồn tham khảo được diễn giải và áp dụng cho thiết kế riêng. Không sao chép một sản phẩm hoàn chỉnh để thay giao diện. Các tài liệu pattern giải thích cơ chế, còn bằng chứng triển khai nằm ở mã và test của dự án.') +
        bullets('[1] COURSE PROJECT SPECIFICATION.pdf, tài liệu đề bài người dùng cung cấp; các mục 4, 7, 9–13.',
                '[2] Chris Richardson, <a href="https://microservices.io/patterns/data/saga.html">Pattern: Saga</a>, microservices.io.',
                '[3] Chris Richardson, <a href="https://microservices.io/patterns/data/transactional-outbox.html">Transactional Outbox</a>, microservices.io.',
                '[4] Chris Richardson, <a href="https://microservices.io/patterns/communication-style/idempotent-consumer.html">Idempotent Consumer</a>, microservices.io.',
                '[5] SQLite, <a href="https://www.sqlite.org/isolation.html">Isolation in SQLite</a> và <a href="https://www.sqlite.org/lang_transaction.html">Transaction</a>.',
                '[6] Python Software Foundation, <a href="https://docs.python.org/3/library/http.server.html">http.server</a>, <a href="https://docs.python.org/3/library/sqlite3.html">sqlite3</a>, <a href="https://docs.python.org/3/library/hashlib.html">hashlib</a>.') +
        p('Công bố sử dụng AI: mã và tài liệu có AI hỗ trợ. Nhóm phải đọc, kiểm chứng, sửa theo thực tế, hiểu cơ chế và chịu trách nhiệm theo mục 13. Không trình bày bảng phân công đề xuất hoặc kết quả tự động như đóng góp cá nhân chưa xảy ra.'))
    add('Phụ lục: tái lập và bàn giao',
        code('python scripts/start.py --open\npython scripts/test.py\npython tests/test_web.py\npython scripts/demo.py --pause\npython scripts/build_docs.py\npython scripts/export_pdf.py') +
        p('Nguồn bằng chứng: docs/test-results.json, docs/performance.json và log JSONL trong run_directory của kết quả. docs/evidence.jsonl chứa một mẫu sự kiện từ lần chạy gần nhất; xem đủ log runtime khi cần truy vết. Thời gian log UTC; ngày trình bày trong tài liệu theo lịch học phần.') +
        p('Web được kiểm chứng riêng bằng 6 bài proxy và các thao tác trên Edge thật, gồm đặt xe/nhận chuyến/thanh toán, demo tự động, session reload và mobile không tràn ngang. Kết quả: docs/web-test-results.json, docs/browser-results.json. Demo vấn đáp tiếp tục dùng sáu cảnh phân tán trong docs/demo.md; mọi thành viên trình bày phần việc thật.') +
        table(['Trước nộp', 'Người thực hiện'], [('Điền tên, MSSV, lớp, giảng viên và repo; cập nhật bìa', 'Nhóm'),
              ('Commit/PR của từng người, review và hiểu code', 'Từng thành viên'),
              ('Chạy Compose, kiểm tra PDF/font và số đo mới nhất', 'Nhóm'),
              ('GitHub repo, quyền giảng viên, final tag/release', 'Chủ repo'),
              ('Đăng ký nhóm, nộp đúng hạn, demo/vấn đáp', 'Nhóm')]) +
        p('Mốc từ tài liệu đề: nộp báo cáo và source ngày 22/11/2026 qua GitHub; demo/vấn đáp ngày 23/11/2026 và 30/11/2026. Theo thông báo giảng viên nếu thay đổi. Dự án chưa tự push, tạo release hoặc xác nhận nhóm đã nộp bài.'))
    assert len(pages) == 24
    (DOCS / 'report.html').write_text(document(pages), encoding='utf-8')
    slides = [
        ('DS03 · Hệ thống gọi xe', p('6 business microservice · Web + CLI · REST · Durable MQ · Saga') + p('Nhóm / lớp / MSSV: hoàn thiện theo docs/team.md') + p('Bản triển khai và kiểm chứng: 03/11/2026')),
        ('Bài toán và tiêu chí', bullets('Đăng ký hai vai trò; driver cập nhật vị trí và trạng thái.', 'Booking → matching → accept/reject → hoàn tất → payment.', 'Không double-book; retry/dedup/DLQ; compensation; phục hồi thật.')),
        ('Kiến trúc và dữ liệu', '<div class="diagram">Identity · Driver · Trip · Matching · Payment · Notification<br>mỗi service một process và một database<br>REST đồng bộ + Broker bất đồng bộ<br>Broker là hạ tầng, không tính business service</div>'),
        ('Luồng nghiệp vụ', '<div class="diagram">Trip requested → MQ → Matching → REST Driver reserve<br>MQ → Trip offered → accept → start → complete<br>MQ → Payment → MQ → Trip terminal + Driver release</div>'),
        ('Không gán hai chuyến cho một tài xế', bullets('BEGIN IMMEDIATE: chọn available và giữ active_trip cùng transaction.', 'Reservation idempotent theo trip_id; một passenger chỉ có một chuyến active.', 'Version guard: hai lệnh accept/reject cùng phiên bản chỉ một thắng.')),
        ('Message reliability', bullets('Outbox commit cùng state; publish lại cùng event ID nếu mất ACK.', 'Broker lưu bền; claim/lease/receipt; bounded retry; DLQ/redrive.', 'Inbox commit cùng tác dụng; ACK sau commit; at-least-once + dedup.')),
        ('Saga và compensation', bullets('Cancel / reject / deadline → cancelled → giải phóng tài xế.', 'Payment decline → payment_failed + ledger declined + release.', 'Tombstone xử lý cancellation trước reserve; terminal không hồi sinh.')),
        ('Demo trực tiếp · Web và lỗi phân tán', bullets('Web: chuẩn bị demo → đặt xe → đổi vai trò tài xế → hoàn tất.', 'Hai khách tranh một driver; kill/restart Payment và Broker.', 'Driver fail → retry/DLQ/redrive; decline → compensation.') + code('python scripts/start.py --open\npython scripts/demo.py --pause')),
        ('Kết quả kiểm thử', p(f'<strong>{passed}/{results["tests"]} đạt</strong> · {results["duration_seconds"]} giây') + bullets('11 chức năng · 3 đồng thời · 6 lỗi/phục hồi.', '3 bảo mật/dữ liệu sai · 1 thực nghiệm hiệu năng.', '7 process thật, HTTP thật, kill/restart thật; JSON/log làm bằng chứng.')),
        ('Hiệu năng · phạm vi đo', p(f'100 GET /trips có auth · 10 clients · localhost') + table(['Throughput', 'p50', 'p95', 'Thành công'], [(str(perf['throughput_rps'])+' req/s', str(perf['p50_ms'])+' ms', str(perf['p95_ms'])+' ms', '100/100')]) + p('Một lần chạy; chưa đo booking throughput, WAN hoặc CPU/RAM. Không suy rộng thành SLA.')),
        ('Bảo mật và giới hạn', bullets('Hash/salt, token HMAC/TTL, role/owner; web proxy chặn internal API.', 'Chưa TLS/mTLS, rate limit/revoke, broker HA hoặc mất đĩa.', f'Web + CLI; sơ đồ/tiền mô phỏng. Docker backend: {docker_passed}/8 ca chọn lọc đạt.')),
        ('Bàn giao và vấn đáp', bullets('Điền thông tin nhóm, commit thật từng người, GitHub access và final tag.', 'Giải thích reserve atomic, outbox/inbox, late event, Saga và failure model.', 'Nguồn: đề bài; microservices.io Saga/Outbox/Idempotent Consumer; SQLite/Python docs. AI có hỗ trợ, nhóm chịu trách nhiệm kiểm chứng.')),
    ]
    (DOCS / 'slides.html').write_text(document(slides, slides=True), encoding='utf-8')
    # Copy only structured, non-secret log fields already designed for audit.
    run_dir = Path(results.get('run_directory', ''))
    records = []
    if run_dir.is_dir():
        for logfile in sorted((run_dir / 'logs').glob('*.jsonl')):
            chosen = []
            for line in logfile.read_text(encoding='utf-8', errors='replace').splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get('event') in ('service.started', 'trip.transition', 'event.enqueued',
                                          'event.processed', 'event.retry', 'outbox.retry',
                                          'delivery.dead', 'delivery.redrive'):
                    chosen.append(event)
            records.extend(chosen[:12] + [e for e in chosen[12:] if e['event'] in
                                         ('delivery.dead', 'delivery.redrive', 'event.retry')][:10])
    (DOCS / 'evidence.jsonl').write_text('\n'.join(json.dumps(e, ensure_ascii=False) for e in records)+'\n', encoding='utf-8')
    print(f'Generated report.html ({len(pages)} pages), slides.html ({len(slides)} slides), evidence.jsonl.')


if __name__ == '__main__':
    main()
