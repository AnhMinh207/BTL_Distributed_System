"""Durable, fan-out message queue with leases, acknowledgements and dead letters."""
import json
import os
import time

from .common import Service, SUBSCRIPTIONS, Problem, internal, require, text_field, uid, log

PRODUCERS = {'trip': {'trip.requested', 'trip.accepted', 'trip.started', 'trip.completed', 'trip.cancelled'},
             'matching': {'driver.reserved', 'matching.failed'},
             'payment': {'payment.succeeded', 'payment.failed'}}


class Broker(Service):
    def __init__(self):
        super().__init__('broker')
        self.db.schema('''
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, envelope TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS deliveries(queue TEXT, event_id TEXT, state TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0, available REAL DEFAULT 0, lease REAL DEFAULT 0,
                receipt TEXT, error TEXT, PRIMARY KEY(queue,event_id));
            CREATE INDEX IF NOT EXISTS ready ON deliveries(queue,state,available);
        ''')

    def dispatch(self, method, path, body, headers, corr):
        internal(headers)
        if method == 'POST' and path == '/events':
            for key in ['id', 'topic', 'producer', 'correlation_id']:
                text_field(body, key)
            require(body['topic'] in SUBSCRIPTIONS and
                    body['topic'] in PRODUCERS.get(body['producer'], set()), 400, 'Unknown producer/topic')
            require(isinstance(body.get('payload'), dict), 400, 'Invalid payload')
            require(type(body.get('timestamp')) in (float, int), 400, 'Invalid timestamp')
            encoded = json.dumps(body, sort_keys=True, allow_nan=False)
            with self.db.tx() as db:
                old = db.execute('SELECT envelope FROM events WHERE id=?', (body['id'],)).fetchone()
                if old:
                    require(old['envelope'] == encoded, 409, 'Event ID reused with different content')
                    return {'published': True, 'duplicate': True}
                db.execute('INSERT INTO events VALUES(?,?)', (body['id'], encoded))
                for queue in SUBSCRIPTIONS[body['topic']]:
                    db.execute('INSERT INTO deliveries(queue,event_id) VALUES(?,?)', (queue, body['id']))
            log('broker', 'event.enqueued', body['correlation_id'], event_id=body['id'],
                topic=body['topic'], result='durable')
            return {'published': True, 'duplicate': False}
        if method == 'GET' and path in ('/stats', '/dead-letters'):
            with self.db.connect() as db:
                if path == '/stats':
                    return {'queues': [dict(r) for r in db.execute(
                        'SELECT queue,state,COUNT(*) AS count FROM deliveries GROUP BY queue,state')]}
                return {'messages': [dict(r) for r in db.execute(
                    "SELECT * FROM deliveries WHERE state='dead' ORDER BY rowid LIMIT 100")]}
        parts = path.strip('/').split('/')
        if method == 'GET' and len(parts) == 3 and parts[0] == 'queues':
            with self.db.connect() as db:
                row = db.execute('SELECT queue,event_id,state,attempts,error FROM deliveries '
                                 'WHERE queue=? AND event_id=?', (parts[1], parts[2])).fetchone()
            require(row is not None, 404, 'Delivery not found')
            return dict(row)
        if method == 'POST' and len(parts) == 3 and parts[0] == 'queues':
            queue, action = parts[1:]
            require(queue in {q for qs in SUBSCRIPTIONS.values() for q in qs}, 404, 'Unknown queue')
            now = time.time()
            maximum = int(os.getenv('MAX_ATTEMPTS', '5'))
            with self.db.tx() as db:
                if action == 'claim':
                    db.execute("UPDATE deliveries SET state=CASE WHEN attempts>=? THEN 'dead' ELSE 'pending' END,"
                               "error='Lease expired',available=? WHERE queue=? AND state='inflight' AND lease<?",
                               (maximum, now, queue, now))
                    row = db.execute("SELECT d.event_id,e.envelope FROM deliveries d JOIN events e "
                                     "ON e.id=d.event_id WHERE d.queue=? AND d.state='pending' AND d.available<=? "
                                     "ORDER BY d.rowid LIMIT 1", (queue, now)).fetchone()
                    if not row:
                        return {'event': None}
                    receipt = uid()
                    db.execute("UPDATE deliveries SET state='inflight',attempts=attempts+1,lease=?,receipt=? "
                               "WHERE queue=? AND event_id=?",
                               (now + float(os.getenv('LEASE_SECONDS', '3')), receipt, queue, row['event_id']))
                    return {'event': json.loads(row['envelope']), 'receipt': receipt}
                require(action in ('ack', 'nack', 'redrive'), 404, 'Unknown action')
                event_id = text_field(body, 'event_id')
                row = db.execute('SELECT * FROM deliveries WHERE queue=? AND event_id=?',
                                 (queue, event_id)).fetchone()
                require(row is not None, 404, 'Delivery not found')
                if action == 'redrive':
                    require(row['state'] == 'dead', 409, 'Only dead messages can be redriven')
                    db.execute("UPDATE deliveries SET state='pending',attempts=0,available=0,error=NULL "
                               'WHERE queue=? AND event_id=?', (queue, event_id))
                    log('broker', 'delivery.redrive', corr, event_id=event_id, queue=queue, result='pending')
                    return {'redriven': True}
                require(row['state'] == 'inflight' and row['receipt'] == body.get('receipt') and row['lease'] >= now,
                        409, 'Stale delivery receipt')
                state = 'done' if action == 'ack' else ('dead' if row['attempts'] >= maximum else 'pending')
                delay=min(8,.2*2**row['attempts'])
                if 'circuit open' in str(body.get('error','')).lower():
                    delay=max(delay,float(os.getenv('CIRCUIT_COOLDOWN','2'))+.1)
                db.execute('UPDATE deliveries SET state=?,available=?,error=? WHERE queue=? AND event_id=?',
                           (state, now + delay, str(body.get('error', ''))[:500],
                            queue, event_id))
                log('broker', 'delivery.' + state, corr, queue=queue, event_id=event_id, result=state)
                return {'state': state}
        raise Problem(404, 'Route not found')
