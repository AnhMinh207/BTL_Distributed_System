import json
import time

from .common import Service, Problem, require, actor, internal, coordinates, text_field, distance


class Driver(Service):
    def __init__(self):
        super().__init__('driver')
        self.db.schema('''
            CREATE TABLE IF NOT EXISTS drivers(id TEXT PRIMARY KEY, location TEXT NOT NULL,
                status TEXT NOT NULL, active_trip TEXT UNIQUE, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS reservations(trip_id TEXT PRIMARY KEY, driver_id TEXT,
                state TEXT NOT NULL);
        ''')

    def dispatch(self, method, path, body, headers, corr):
        if path == '/drivers/me' and method == 'POST':
            user = actor(headers)
            require(user['role'] == 'driver', 403, 'Driver role required')
            location = coordinates(body, 'location')
            status = body.get('status')
            require(status in ('available', 'offline', 'busy'), 400, 'Invalid status')
            with self.db.tx() as db:
                old = db.execute('SELECT * FROM drivers WHERE id=?', (user['sub'],)).fetchone()
                require(not old or not old['active_trip'] or status == 'busy', 409, 'Driver has active trip')
                require(status != 'busy' or (old and old['active_trip']), 409, 'Busy requires active trip')
                db.execute('INSERT INTO drivers VALUES(?,?,?,NULL,?) ON CONFLICT(id) DO UPDATE SET '
                           'location=excluded.location,status=excluded.status,updated=excluded.updated',
                           (user['sub'], json.dumps(location), status, time.time()))
            return {'id': user['sub'], 'status': status, 'location': location}
        if path == '/drivers/me' and method == 'GET':
            user = actor(headers)
            require(user['role'] == 'driver', 403, 'Driver role required')
            with self.db.connect() as db:
                row = db.execute('SELECT * FROM drivers WHERE id=?', (user['sub'],)).fetchone()
            require(row is not None, 404, 'Driver profile not found')
            result = dict(row)
            result['location'] = json.loads(result['location'])
            return result
        internal(headers)
        if path == '/internal/supply' and method == 'POST':
            pickup=coordinates(body,'pickup')
            with self.db.connect() as db:
                rows=db.execute("SELECT location,updated FROM drivers WHERE status='available' AND active_trip IS NULL").fetchall()
            return {'available':sum(time.time()-r['updated']<300 and distance(pickup,json.loads(r['location']))<=20 for r in rows)}
        if path == '/internal/reserve' and method == 'POST':
            trip = text_field(body, 'trip_id')
            pickup = coordinates(body, 'pickup')
            with self.db.tx() as db:
                old = db.execute('SELECT * FROM reservations WHERE trip_id=?', (trip,)).fetchone()
                if old:
                    return {'driver_id': old['driver_id'] if old['state'] == 'reserved' else None}
                # BEGIN IMMEDIATE serializes reserve + release and prevents lost updates.
                candidates = db.execute("SELECT * FROM drivers WHERE status='available' AND active_trip IS NULL").fetchall()
                # Presence lease: driver must refresh status/location at least every 5 minutes.
                candidates = [r for r in candidates if time.time() - r['updated'] < 300
                              and distance(pickup, json.loads(r['location'])) <= 20]
                candidates.sort(key=lambda r: (distance(pickup, json.loads(r['location'])), r['id']))
                if not candidates:
                    db.execute("INSERT INTO reservations VALUES(?,NULL,'unavailable')", (trip,))
                    return {'driver_id': None}
                driver_id = candidates[0]['id']
                db.execute("UPDATE drivers SET status='busy',active_trip=? WHERE id=? AND active_trip IS NULL",
                           (trip, driver_id))
                db.execute("INSERT INTO reservations VALUES(?,?,'reserved')", (trip, driver_id))
                return {'driver_id': driver_id}
        raise Problem(404, 'Route not found')

    def handle_event(self, db, event):
        trip = event['payload']['trip_id']
        db.execute("UPDATE drivers SET active_trip=NULL,status='available' WHERE active_trip=?", (trip,))
        # Tombstone makes a cancellation arriving before reserve safe.
        db.execute("INSERT INTO reservations VALUES(?,NULL,'released') ON CONFLICT(trip_id) "
                   "DO UPDATE SET state='released'", (trip,))
