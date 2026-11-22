from .common import Service, call, service_url, internal_headers, Problem


class Matching(Service):
    def __init__(self):
        super().__init__('matching')
        self.db.schema('''CREATE TABLE IF NOT EXISTS matches(
            trip_id TEXT PRIMARY KEY, driver_id TEXT, status TEXT NOT NULL);''')

    def before_event(self, event):
        _, result = call(service_url('driver') + '/internal/reserve', 'POST',
                         {'trip_id': event['payload']['trip_id'], 'pickup': event['payload']['pickup']},
                         {**internal_headers(), 'X-Correlation-ID': event['correlation_id']})
        return {**event, 'driver_id': result['driver_id']}

    def handle_event(self, db, event):
        p = event['payload']
        driver_id = event['driver_id']
        db.execute('INSERT OR IGNORE INTO matches VALUES(?,?,?)',
                   (p['trip_id'], driver_id, 'matched' if driver_id else 'failed'))
        self.emit(db, 'driver.reserved' if driver_id else 'matching.failed',
                  {**p, 'driver_id': driver_id}, event['correlation_id'])

    def dispatch(self, method, path, body, headers, corr):
        raise Problem(404, 'Route not found')
