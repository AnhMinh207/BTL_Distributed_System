import base64
import hashlib
import hmac
import json
import math
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PORTS = dict(broker=8100, identity=8101, driver=8102, trip=8103,
             matching=8104, payment=8105, notification=8106)
SUBSCRIPTIONS = {
    'trip.requested': ['matching', 'notification'],
    'driver.reserved': ['trip', 'notification'],
    'matching.failed': ['trip', 'notification'],
    'trip.accepted': ['notification'],
    'trip.started': ['notification'],
    'trip.completed': ['payment', 'notification'],
    'trip.cancelled': ['driver', 'notification'],
    'payment.succeeded': ['trip', 'driver', 'notification'],
    'payment.failed': ['trip', 'driver', 'notification'],
}
MAX_BODY = 65536
_LOG_LOCK = threading.Lock()


def uid():
    return str(uuid.uuid4())


def log(node, event, correlation_id='-', **fields):
    record = json.dumps(dict(timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                             node=node, event=event, correlation_id=correlation_id, **fields), ensure_ascii=False)
    # HTTP handlers and workers share stdout inside one service; keep each JSON line intact.
    with _LOG_LOCK:
        print(record, flush=True)


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def require(condition, status, message):
    if not condition:
        raise Problem(status, message)


def text_field(data, key, minimum=1, maximum=128):
    value = data.get(key)
    require(isinstance(value, str) and minimum <= len(value) <= maximum, 400, f'Invalid {key}')
    require(not any(ord(c) < 32 for c in value), 400, f'Invalid {key}')
    return value


def coordinates(data, key):
    value = data.get(key)
    require(isinstance(value, list) and len(value) == 2, 400, f'Invalid {key}')
    for n, limit in zip(value, [90, 180]):
        require(type(n) in (int, float) and math.isfinite(n) and abs(n) <= limit,
                400, f'Invalid {key}')
    return value


def distance(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat, dlon = lat2 - lat1, math.radians(b[1] - a[1])
    v = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(v)))


def service_url(name):
    return os.getenv(name.upper() + '_URL', f'http://127.0.0.1:{PORTS[name]}')


def internal_headers():
    return {'X-Service-Key': os.environ['SERVICE_KEY']}


def call(url, method='GET', data=None, headers=None, timeout=2):
    body = None if data is None else json.dumps(data, allow_nan=False).encode()
    request = Request(url, data=body, method=method,
                      headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.load(response)
    except HTTPError as e:
        try:
            result = json.load(e)
        except (ValueError, OSError):
            result = {'error': str(e)}
        raise Problem(e.code, result.get('error', str(e))) from e
    except (URLError, TimeoutError, OSError) as e:
        raise Problem(503, 'Service unavailable') from e


def encode_token(user):
    payload = dict(sub=user['id'], role=user['role'], exp=int(time.time()) + int(os.getenv('TOKEN_TTL', '3600')))
    raw = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True).encode()).decode().rstrip('=')
    sig = hmac.new(os.environ['AUTH_SECRET'].encode(), raw.encode(), hashlib.sha256).hexdigest()
    return raw + '.' + sig


def actor(headers):
    value = headers.get('Authorization', '')
    require(value.startswith('Bearer '), 401, 'Bearer token required')
    try:
        raw, sig = value[7:].split('.')
        expected = hmac.new(os.environ['AUTH_SECRET'].encode(), raw.encode(), hashlib.sha256).hexdigest()
        require(hmac.compare_digest(sig, expected), 401, 'Invalid token')
        data = json.loads(base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)))
        require(data['exp'] > time.time() and data['role'] in ('passenger', 'driver'), 401, 'Expired token')
        return data
    except (ValueError, KeyError, TypeError):
        raise Problem(401, 'Invalid token')


def internal(headers):
    require(hmac.compare_digest(headers.get('X-Service-Key', ''), os.environ['SERVICE_KEY']),
            403, 'Service authentication required')


class Database:
    def __init__(self, name):
        root = Path(os.getenv('DATA_DIR', 'runtime')) / name
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / 'state.db'
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, processed_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, envelope TEXT NOT NULL,
                    published INTEGER NOT NULL DEFAULT 0);
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=10000')
        return db

    @contextmanager
    def tx(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def schema(self, sql):
        with self.connect() as db:
            db.executescript(sql)


class Service:
    def __init__(self, name):
        self.name = name
        self.db = Database(name)
        self.stop = threading.Event()

    def emit(self, db, topic, payload, correlation_id):
        event = dict(id=uid(), topic=topic, producer=self.name, timestamp=time.time(),
                     correlation_id=correlation_id, payload=payload)
        db.execute('INSERT INTO outbox(id,envelope) VALUES(?,?)', (event['id'], json.dumps(event)))

    def dispatch(self, method, path, body, headers, correlation):
        raise Problem(404, 'Route not found')

    def handle_event(self, db, event):
        pass

    def before_event(self, event):
        return event

    def tick(self):
        pass

    def publish_loop(self):
        while not self.stop.wait(.15):
            try:
                self.tick()
                with self.db.connect() as db:
                    rows = db.execute('SELECT * FROM outbox WHERE published=0 LIMIT 30').fetchall()
                for row in rows:
                    event = json.loads(row['envelope'])
                    call(service_url('broker') + '/events', 'POST', event, internal_headers())
                    with self.db.tx() as db:
                        db.execute('UPDATE outbox SET published=1 WHERE id=?', (row['id'],))
                    log(self.name, 'outbox.published', event['correlation_id'], event_id=event['id'], result='ok')
            except Exception as e:
                log(self.name, 'outbox.retry', error=str(e), result='pending')
                self.stop.wait(.5)

    def consume_loop(self):
        while not self.stop.wait(.1):
            delivery = None
            try:
                _, delivery = call(service_url('broker') + '/queues/' + self.name + '/claim',
                                   'POST', {}, internal_headers())
                if not delivery.get('event'):
                    continue
                event = delivery['event']
                with self.db.connect() as db:
                    seen = db.execute('SELECT 1 FROM inbox WHERE id=?', (event['id'],)).fetchone()
                if not seen:
                    prepared = self.before_event(event)
                    with self.db.tx() as db:
                        if not db.execute('SELECT 1 FROM inbox WHERE id=?', (event['id'],)).fetchone():
                            self.handle_event(db, prepared)
                            db.execute('INSERT INTO inbox VALUES(?,?)', (event['id'], time.time()))
                    log(self.name, 'event.processed', event['correlation_id'], event_id=event['id'],
                        topic=event['topic'], result='ok')
                else:
                    log(self.name, 'event.duplicate', event['correlation_id'], event_id=event['id'], result='ignored')
                call(service_url('broker') + '/queues/' + self.name + '/ack', 'POST',
                     {'event_id': event['id'], 'receipt': delivery['receipt']}, internal_headers())
            except Exception as e:
                log(self.name, 'event.retry', error=str(e), result='retry')
                if delivery and delivery.get('event'):
                    try:
                        call(service_url('broker') + '/queues/' + self.name + '/nack', 'POST',
                             {'event_id': delivery['event']['id'], 'receipt': delivery['receipt'],
                              'error': str(e)[:500]}, internal_headers())
                    except Problem:
                        pass
                self.stop.wait(.3)

    def run(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.0'

            def log_message(self, *_):
                pass

            def do_GET(self):
                self.handle_request()

            def do_POST(self):
                self.handle_request()

            def handle_request(self):
                self.connection.settimeout(5)
                corr = self.headers.get('X-Correlation-ID', uid())
                if not re.fullmatch(r'[A-Za-z0-9._-]{1,128}', corr):
                    corr = uid()
                started = time.monotonic()
                status = 200
                try:
                    length = self.headers.get('Content-Length', '0')
                    require(length.isdigit() and int(length) <= MAX_BODY, 413, 'Body too large')
                    require(not self.headers.get('Transfer-Encoding'), 400, 'Unsupported encoding')
                    body = json.loads(self.rfile.read(int(length))) if int(length) else {}
                    require(isinstance(body, dict), 400, 'Expected JSON object')
                    if self.path == '/health' and self.command == 'GET':
                        with app.db.connect() as db:
                            db.execute('SELECT 1').fetchone()
                        result = dict(service=app.name, status='up')
                    else:
                        result = app.dispatch(self.command, self.path.split('?')[0], body, self.headers, corr)
                except Problem as e:
                    status, result = e.status, {'error': e.message}
                except (ValueError, UnicodeError):
                    status, result = 400, {'error': 'Malformed JSON'}
                except Exception as e:
                    status, result = 500, {'error': 'Internal server error'}
                    log(app.name, 'http.error', corr, error=str(e), result='failed')
                data = json.dumps(result, ensure_ascii=False, allow_nan=False).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('X-Correlation-ID', corr)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                try:
                    self.wfile.write(data)
                except OSError:
                    pass
                log(app.name, 'http.request', corr, method=self.command, path=self.path.split('?')[0],
                    result=status, duration_ms=round((time.monotonic()-started)*1000, 2))

        if self.name != 'broker':
            threading.Thread(target=self.publish_loop, daemon=True).start()
            if any(self.name in subscribers for subscribers in SUBSCRIPTIONS.values()):
                threading.Thread(target=self.consume_loop, daemon=True).start()
        host = os.getenv('HOST', '127.0.0.1')
        port = int(os.getenv('PORT', str(PORTS[self.name])))
        log(self.name, 'service.started', result='listening', host=host, port=port)
        server = ThreadingHTTPServer((host, port), Handler)
        server.daemon_threads = True
        try:
            server.serve_forever()
        finally:
            self.stop.set()
            server.server_close()
