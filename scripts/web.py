"""Local web UI and strictly allowlisted, same-origin public API proxy.

No business database access, no service key forwarded, no privileged broker API.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cluster import environment
from src.common import MAX_BODY, PORTS, Problem, call, log, require, service_url, uid

ASSETS = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'),
          '/app.js': ('app.js', 'text/javascript'), '/styles.css': ('styles.css', 'text/css'),
          '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
ROUTES = {
    'identity': [('POST', r'/register'), ('POST', r'/login')],
    'driver': [('GET', r'/drivers/me'), ('POST', r'/drivers/me')],
    'trip': [('GET', r'/trips'), ('POST', r'/trips'), ('GET', r'/trips/[a-zA-Z0-9-]+'),
             ('POST', r'/trips/[a-zA-Z0-9-]+/(accept|reject|start|complete|cancel)')],
    'payment': [('GET', r'/payments')],
    'notification': [('GET', r'/notifications')],
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.respond()

    def do_POST(self):
        self.respond()

    def respond(self):
        correlation = self.headers.get('X-Correlation-ID', uid())
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,128}', correlation):
            correlation = uid()
        status, mime = 200, 'application/json'
        path = urlsplit(self.path).path
        try:
            self.connection.settimeout(5)
            if self.command == 'GET' and path in ASSETS:
                filename, mime = ASSETS[path]
                result = (ROOT / 'src' / 'web' / filename).read_bytes()
            elif self.command == 'GET' and path == '/health':
                result = {'service': 'web', 'status': 'up'}
            elif self.command == 'GET' and path == '/api/status':
                def health(name):
                    try:
                        return name, call(service_url(name) + '/health', timeout=1)[1]
                    except Problem:
                        return name, {'service': name, 'status': 'down'}
                with ThreadPoolExecutor(max_workers=7) as pool:
                    result = {'services': dict(pool.map(health, PORTS))}
            else:
                parts = path.split('/', 3)
                require(len(parts) == 4 and parts[1] == 'api', 404, 'Route not found')
                name, route = parts[2], '/' + parts[3]
                require(any(method == self.command and re.fullmatch(pattern, route)
                            for method, pattern in ROUTES.get(name, [])), 404, 'Route not found')
                data = None
                if self.command == 'POST':
                    origin = self.headers.get('Origin')
                    require(not origin or origin == 'http://' + self.headers.get('Host', ''),
                            403, 'Cross-origin request denied')
                    length = self.headers.get('Content-Length', '0')
                    require(length.isdigit() and int(length) <= MAX_BODY, 413, 'Body too large')
                    require(not self.headers.get('Transfer-Encoding'), 400, 'Unsupported encoding')
                    data = json.loads(self.rfile.read(int(length))) if int(length) else {}
                    require(isinstance(data, dict), 400, 'Expected JSON object')
                # Deliberately do not forward X-Service-Key, cookies or arbitrary headers.
                headers = {'X-Correlation-ID': correlation}
                for key in ('Authorization', 'Idempotency-Key'):
                    if self.headers.get(key):
                        headers[key] = self.headers[key]
                status, result = call(service_url(name) + route, self.command, data, headers, timeout=3)
        except Problem as e:
            status, result = e.status, {'error': e.message}
        except (ValueError, UnicodeError):
            status, result = 400, {'error': 'Malformed JSON'}
        except Exception as e:
            status, result = 500, {'error': 'Web gateway error'}
            log('web', 'proxy.error', correlation, error=str(e), result='failed')
        if not isinstance(result, bytes):
            result = json.dumps(result, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(result)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Correlation-ID', correlation)
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        try:
            self.wfile.write(result)
        except OSError:
            pass
        if path.startswith('/api/') and path != '/api/status':
            log('web', 'http.request', correlation, method=self.command, path=path, result=status)


def main():
    os.environ.update(environment())
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.getenv('WEB_PORT', '8080')))
    parser.add_argument('--host', default=os.getenv('WEB_HOST', '127.0.0.1'))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    print(f'GoRide web: http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
