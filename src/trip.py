import hashlib
import json
import os
import re
import time

from .common import Service, Problem, require, actor, coordinates, distance, uid, log

TERMINAL = {'completed', 'cancelled', 'payment_failed'}


class Trip(Service):
    def __init__(self):
        super().__init__('trip')
        self.db.schema('''
            CREATE TABLE IF NOT EXISTS trips(id TEXT PRIMARY KEY, passenger_id TEXT NOT NULL,
                driver_id TEXT, state TEXT NOT NULL, pickup TEXT NOT NULL, destination TEXT NOT NULL,
                fare INTEGER NOT NULL, payment_mode TEXT NOT NULL, version INTEGER NOT NULL,
                correlation_id TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
                deadline REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS requests(passenger_id TEXT, key TEXT, fingerprint TEXT NOT NULL,
                trip_id TEXT NOT NULL, PRIMARY KEY(passenger_id,key));
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_passenger ON trips(passenger_id)
                WHERE state NOT IN ('completed','cancelled','payment_failed');
        ''')

    def view(self, row):
        result = dict(row)
        for key in ('pickup', 'destination'):
            result[key] = json.loads(result[key])
        return result

    def payload(self, row):
        return self.view(row)

    def move(self, db, row, state, topic=None, driver_id=None):
        assigned = driver_id if driver_id is not None else row['driver_id']
        deadline = time.time() + float(os.getenv('OFFER_TIMEOUT', '120')) if state == 'offered' else row['deadline']
        db.execute('UPDATE trips SET state=?,driver_id=?,version=version+1,updated=?,deadline=? WHERE id=?',
                   (state, assigned, time.time(), deadline, row['id']))
        updated = db.execute('SELECT * FROM trips WHERE id=?', (row['id'],)).fetchone()
        if topic:
            self.emit(db, topic, {**self.payload(updated), 'trip_id': updated['id']}, row['correlation_id'])
        log('trip', 'trip.transition', row['correlation_id'], trip_id=row['id'],
            previous=row['state'], state=state, version=updated['version'], result='transaction_pending_commit')
        return self.view(updated)

    def dispatch(self, method, path, body, headers, corr):
        user = actor(headers)
        if path == '/trips' and method == 'POST':
            require(user['role'] == 'passenger', 403, 'Passenger role required')
            pickup, destination = coordinates(body, 'pickup'), coordinates(body, 'destination')
            mode = body.get('payment_mode', 'success')
            require(mode in ('success', 'decline'), 400, 'Invalid simulated payment mode')
            key = headers.get('Idempotency-Key', '')
            require(re.fullmatch(r'[A-Za-z0-9._-]{8,128}', key), 400, 'Idempotency-Key required (8-128 chars)')
            normalized = dict(pickup=pickup, destination=destination, payment_mode=mode)
            fingerprint = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
            with self.db.tx() as db:
                old = db.execute('SELECT * FROM requests WHERE passenger_id=? AND key=?',
                                 (user['sub'], key)).fetchone()
                if old:
                    require(old['fingerprint'] == fingerprint, 409, 'Idempotency key reused with different request')
                    return self.view(db.execute('SELECT * FROM trips WHERE id=?', (old['trip_id'],)).fetchone())
                require(not db.execute("SELECT 1 FROM trips WHERE passenger_id=? AND state NOT IN "
                                       "('completed','cancelled','payment_failed')", (user['sub'],)).fetchone(),
                        409, 'Passenger already has active trip')
                trip_id = uid()
                fare = 12000 + round(distance(pickup, destination) * 8000)
                now = time.time()
                db.execute('INSERT INTO trips VALUES(?,?,NULL,?,?,?,?,?,1,?,?,?,?)',
                           (trip_id, user['sub'], 'requested', json.dumps(pickup), json.dumps(destination),
                            fare, mode, corr, now, now, now + float(os.getenv('SAGA_TIMEOUT', '60'))))
                db.execute('INSERT INTO requests VALUES(?,?,?,?)', (user['sub'], key, fingerprint, trip_id))
                row = db.execute('SELECT * FROM trips WHERE id=?', (trip_id,)).fetchone()
                self.emit(db, 'trip.requested', {**self.payload(row), 'trip_id': trip_id}, corr)
                return self.view(row)
        if path == '/trips' and method == 'GET':
            column = 'passenger_id' if user['role'] == 'passenger' else 'driver_id'
            with self.db.connect() as db:
                rows = db.execute(f'SELECT * FROM trips WHERE {column}=? ORDER BY created DESC LIMIT 100',
                                  (user['sub'],)).fetchall()
            return {'trips': [self.view(r) for r in rows]}
        parts = path.strip('/').split('/')
        require(len(parts) in (2, 3) and parts[0] == 'trips', 404, 'Route not found')
        with self.db.tx() as db:
            row = db.execute('SELECT * FROM trips WHERE id=?', (parts[1],)).fetchone()
            require(row is not None, 404, 'Trip not found')
            own = row['passenger_id'] == user['sub'] if user['role'] == 'passenger' else row['driver_id'] == user['sub']
            require(own, 403, 'Trip access denied')
            if method == 'GET' and len(parts) == 2:
                return self.view(row)
            require(method == 'POST' and len(parts) == 3, 404, 'Route not found')
            action = parts[2]
            # Version preconditions prevent replay/out-of-order lifecycle commands.
            require(type(body.get('version')) is int and body['version'] == row['version'],
                    409, 'Version conflict; read current trip before retry')
            if action == 'cancel':
                require(user['role'] == 'passenger', 403, 'Passenger role required')
                require(row['state'] in ('requested', 'offered', 'accepted'), 409, 'Trip cannot be cancelled')
                return self.move(db, row, 'cancelled', 'trip.cancelled')
            require(user['role'] == 'driver', 403, 'Driver role required')
            transitions = {'accept': ('offered', 'accepted', 'trip.accepted'),
                           'reject': ('offered', 'cancelled', 'trip.cancelled'),
                           'start': ('accepted', 'in_progress', 'trip.started'),
                           'complete': ('in_progress', 'awaiting_payment', 'trip.completed')}
            require(action in transitions, 404, 'Unknown action')
            expected, state, topic = transitions[action]
            require(row['state'] == expected, 409, 'Invalid trip transition')
            return self.move(db, row, state, topic)

    def handle_event(self, db, event):
        p, topic = event['payload'], event['topic']
        row = db.execute('SELECT * FROM trips WHERE id=?', (p['trip_id'],)).fetchone()
        require(row is not None, 409, 'Unknown trip')
        if topic == 'driver.reserved':
            if row['state'] == 'requested':
                self.move(db, row, 'offered', driver_id=p['driver_id'])
            elif row['state'] in TERMINAL:
                # Late match after deadline/cancellation must be compensated again.
                self.emit(db, 'trip.cancelled', {**self.payload(row), 'trip_id': row['id']}, row['correlation_id'])
        elif topic == 'matching.failed' and row['state'] == 'requested':
            self.move(db, row, 'cancelled', 'trip.cancelled')
        elif topic in ('payment.succeeded', 'payment.failed'):
            if row['state'] == 'awaiting_payment':
                self.move(db, row, 'completed' if topic == 'payment.succeeded' else 'payment_failed')
            elif row['state'] not in TERMINAL:
                raise Problem(409, 'Payment arrived before completion')

    def tick(self):
        with self.db.tx() as db:
            rows = db.execute("SELECT * FROM trips WHERE state IN ('requested','offered') AND deadline<?",
                              (time.time(),)).fetchall()
            for row in rows:
                self.move(db, row, 'cancelled', 'trip.cancelled')
