import json

from .common import Service, actor, require


class Notification(Service):
    def __init__(self):
        super().__init__('notification')
        self.db.schema('''CREATE TABLE IF NOT EXISTS notifications(event_id TEXT, user_id TEXT,
            topic TEXT NOT NULL, trip_id TEXT NOT NULL, timestamp REAL NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(event_id,user_id));''')

    def handle_event(self, db, event):
        p = event['payload']
        for user_id in set(filter(None, [p.get('passenger_id'), p.get('driver_id')])):
            db.execute('INSERT OR IGNORE INTO notifications VALUES(?,?,?,?,?,?)',
                       (event['id'], user_id, event['topic'], p['trip_id'], event['timestamp'], json.dumps(p)))

    def dispatch(self, method, path, body, headers, corr):
        user = actor(headers)
        require(method == 'GET' and path == '/notifications', 404, 'Route not found')
        with self.db.connect() as db:
            rows = db.execute('SELECT event_id,topic,trip_id,timestamp FROM notifications '
                              'WHERE user_id=? ORDER BY timestamp DESC,event_id LIMIT 100', (user['sub'],)).fetchall()
        return {'notifications': [dict(r) for r in rows]}
