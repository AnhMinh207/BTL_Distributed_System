"""Small per-endpoint circuit breaker with one half-open probe."""
import os
import threading
import time
from urllib.parse import urlsplit


class CircuitOpen(Exception):
    pass


class Circuits:
    def __init__(self):
        self.lock = threading.Lock()
        self.entries = {}

    def before(self, url):
        part = urlsplit(url)
        key = part.netloc + part.path
        if os.getenv('CIRCUIT_BREAKER', '1') != '1':
            return None
        with self.lock:
            state = self.entries.setdefault(key, dict(failures=0, until=0, probe=False))
            if state['until']:
                if time.monotonic() < state['until'] or state['probe']:
                    raise CircuitOpen('Dependency circuit open')
                state['probe'] = True
            return key

    def after(self, key, failed):
        if key is None:
            return
        with self.lock:
            state = self.entries[key]
            state['probe'] = False
            if not failed:
                state.update(failures=0, until=0)
            else:
                state['failures'] += 1
                if state['failures'] >= int(os.getenv('CIRCUIT_THRESHOLD', '3')):
                    state['until'] = time.monotonic() + float(os.getenv('CIRCUIT_COOLDOWN', '2'))

    def snapshot(self):
        with self.lock:
            return [{ 'endpoint': key, 'failures': s['failures'],
                      'state': ('half_open' if s['probe'] else 'open') if s['until'] else 'closed',
                      'retry_after_seconds': round(max(0, s['until']-time.monotonic()), 2)}
                    for key,s in self.entries.items() if s['failures'] or s['until']]


CIRCUITS = Circuits()
