"""Best-effort, bounded async telemetry. Business commits never depend on the collector."""
from contextvars import ContextVar
import json
import os
import queue
import socket
import threading
import time
import uuid
from urllib.request import Request, urlopen

TRACE = ContextVar('trace', default={})
PENDING = queue.Queue(maxsize=2000)
START_LOCK = threading.Lock()
started = False


def instance():
    return os.getenv('INSTANCE_ID', socket.gethostname())


def span(trace_id, parent_id=None):
    return dict(trace_id=trace_id, span_id=uuid.uuid4().hex[:16], parent_span_id=parent_id)


def submit(record):
    global started
    if not os.getenv('OBSERVABILITY_URL') or record.get('node') == 'observability':
        return
    path=record.get('path','')
    if path=='/health' or path.endswith(('/claim','/ack')):
        return
    with START_LOCK:
        if not started:
            started = True
            threading.Thread(target=ship, daemon=True).start()
    try:
        PENDING.put_nowait(record)
    except queue.Full:
        pass


def ship():
    while True:
        first = PENDING.get()
        batch = [first]
        while len(batch) < 30:
            try:
                batch.append(PENDING.get_nowait())
            except queue.Empty:
                break
        body = json.dumps({'records': batch}).encode()
        try:
            req = Request(os.environ['OBSERVABILITY_URL']+'/records', data=body,
                          headers={'Content-Type':'application/json','X-Service-Key':os.environ['SERVICE_KEY']})
            with urlopen(req, timeout=1) as response:
                response.read(256)
        except Exception:
            # stdout remains the authoritative local log. No recursive telemetry logging here.
            time.sleep(.3)
