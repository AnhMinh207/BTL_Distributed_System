import time

from .common import Service, actor, require, Problem


class Payment(Service):
    def __init__(self):
        super().__init__('payment')
        self.db.schema('''CREATE TABLE IF NOT EXISTS payments(trip_id TEXT PRIMARY KEY,
            passenger_id TEXT NOT NULL, driver_id TEXT NOT NULL, amount INTEGER NOT NULL,
            state TEXT NOT NULL, created REAL NOT NULL);''')

    def handle_event(self, db, event):
        p = event['payload']
        if db.execute('SELECT 1 FROM payments WHERE trip_id=?', (p['trip_id'],)).fetchone():
            return
        state = 'paid' if p['payment_mode'] == 'success' else 'declined'
        db.execute('INSERT INTO payments VALUES(?,?,?,?,?,?)',
                   (p['trip_id'], p['passenger_id'], p['driver_id'], p['fare'], state, time.time()))
        self.emit(db, 'payment.succeeded' if state == 'paid' else 'payment.failed',
                  {**p, 'payment_state': state}, event['correlation_id'])

    def dispatch(self, method, path, body, headers, corr):
        user = actor(headers)
        require(method == 'GET' and path == '/payments', 404, 'Route not found')
        column = 'passenger_id' if user['role'] == 'passenger' else 'driver_id'
        with self.db.connect() as db:
            return {'payments': [dict(r) for r in db.execute(
                f'SELECT * FROM payments WHERE {column}=? ORDER BY created DESC LIMIT 100', (user['sub'],))]}
