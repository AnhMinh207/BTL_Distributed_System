"""Black-box tests: seven OS processes, real HTTP, persistent independent databases."""
import concurrent.futures
import json
import os
from pathlib import Path
import secrets
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cluster import Cluster
from src.common import PORTS, Problem, call, distance, uid


class SystemTests(unittest.TestCase):
    counter = 0

    @classmethod
    def setUpClass(cls):
        (ROOT / 'docs').mkdir(exist_ok=True)
        cls.run_dir = ROOT / 'runtime' / ('test-' + uid())
        cls.env = os.environ.copy()
        cls.env.update(AUTH_SECRET=secrets.token_hex(32), SERVICE_KEY=secrets.token_hex(32),
                       OPERATIONS_KEY=secrets.token_hex(32), MATCHING_REPLICA_DATA='1',
                       DATA_DIR=str(cls.run_dir / 'data'), HOST='127.0.0.1', MAX_ATTEMPTS='3',
                       LEASE_SECONDS='2', SAGA_TIMEOUT='300', OFFER_TIMEOUT='300', PYTHONUNBUFFERED='1')
        cls.urls = {}
        for name, port in PORTS.items():
            cls.urls[name] = f'http://127.0.0.1:{port + 1000}'
            cls.env[name.upper() + '_URL'] = cls.urls[name]
        # Every child gets its own listening port.
        cls.cluster = Cluster(cls.env, cls.run_dir / 'logs')
        original_start = cls.cluster.start

        def start(name):
            cls.cluster.env['PORT'] = str(PORTS[name] + 1000)
            original_start(name)

        cls.cluster.start = start
        try:
            cls.cluster.start_all()
        except BaseException:
            cls.cluster.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.cluster.close()

    def setUp(self):
        type(self).counter += 1
        self.location = [-30 + self.counter, 106]
        self.destination = [self.location[0] + .015, 106.02]

    def api(self, service, path, method='GET', data=None, user=None, key=None, internal=False):
        headers = {}
        if user:
            headers['Authorization'] = 'Bearer ' + user['token']
        if key:
            headers['Idempotency-Key'] = key
        if internal:
            headers['X-Service-Key'] = self.env['SERVICE_KEY']
        return call(self.urls[service] + path, method, data, headers, timeout=4)[1]

    def register(self, role='passenger'):
        return self.api('identity', '/register', 'POST',
                        {'username': role + uid()[:12], 'password': 'Demo-password-2026!', 'role': role})

    def driver(self):
        driver = self.register('driver')
        self.api('driver', '/drivers/me', 'POST', {'location': self.location, 'status': 'available'}, driver)
        return driver

    def request(self, passenger, mode='success', key=None):
        return self.api('trip', '/trips', 'POST',
                        {'pickup': self.location, 'destination': self.destination, 'payment_mode': mode},
                        passenger, key or uid())

    def wait(self, fn, predicate=lambda value: bool(value), seconds=15):
        deadline = time.monotonic() + seconds
        last = None
        while time.monotonic() < deadline:
            last = fn()
            if predicate(last):
                return last
            time.sleep(.1)
        self.fail('Timed out, last result: ' + str(last))

    def trip_state(self, passenger, trip_id, state):
        return self.wait(lambda: self.api('trip', '/trips/' + trip_id, user=passenger),
                         lambda t: t['state'] in state)

    def offered(self, mode='success'):
        driver, passenger = self.driver(), self.register()
        trip = self.request(passenger, mode)
        return driver, passenger, self.trip_state(passenger, trip['id'], {'offered'})

    def action(self, trip, action, user):
        return self.api('trip', '/trips/' + trip['id'] + '/' + action, 'POST', {'version': trip['version']}, user)

    def finish(self, driver, trip):
        for action in ('accept', 'start', 'complete'):
            trip = self.action(trip, action, driver)
        return trip

    def available(self, driver):
        return self.wait(lambda: self.api('driver', '/drivers/me', user=driver),
                         lambda d: d['status'] == 'available' and d['active_trip'] is None)

    def expect_error(self, status, fn):
        with self.assertRaises(Problem) as caught:
            fn()
        self.assertEqual(status, caught.exception.status)

    def test_F01_registration_and_login(self):
        user = self.register()
        logged = self.api('identity', '/login', 'POST',
                          {'username': user['username'], 'password': 'Demo-password-2026!'})
        self.assertEqual(user['id'], logged['id'])
        self.assertEqual('passenger', logged['role'])
        driver = self.register('driver')
        self.assertEqual('driver', driver['role'])

    def test_F02_driver_status_and_location(self):
        driver = self.driver()
        result = self.api('driver', '/drivers/me', user=driver)
        self.assertEqual(self.location, result['location'])
        self.api('driver', '/drivers/me', 'POST', {'location': self.location, 'status': 'offline'}, driver)
        self.assertEqual('offline', self.api('driver', '/drivers/me', user=driver)['status'])

    def test_F03_complete_ride_and_payment(self):
        driver, passenger, trip = self.offered()
        self.assertEqual(driver['id'], trip['driver_id'])
        self.expect_error(409, lambda: self.api('driver', '/drivers/me', 'POST',
                                              {'location': self.location, 'status': 'available'}, driver))
        self.api('driver', '/drivers/me', 'POST', {'location': self.location, 'status': 'busy'}, driver)
        self.finish(driver, trip)
        self.trip_state(passenger, trip['id'], {'completed'})
        payments = self.wait(lambda: self.api('payment', '/payments', user=passenger)['payments'])
        self.assertEqual(1, len(payments))
        self.assertEqual('paid', payments[0]['state'])
        self.available(driver)

    def test_F04_reject_compensates_reservation(self):
        driver, passenger, trip = self.offered()
        self.action(trip, 'reject', driver)
        self.trip_state(passenger, trip['id'], {'cancelled'})
        self.available(driver)

    def test_F05_no_driver_cancels(self):
        passenger = self.register()
        trip = self.request(passenger)
        self.trip_state(passenger, trip['id'], {'cancelled'})

    def test_F06_notifications_for_both_roles(self):
        driver, passenger, trip = self.offered()
        self.finish(driver, trip)
        for user in (driver, passenger):
            notices = self.wait(lambda: self.api('notification', '/notifications', user=user)['notifications'],
                                lambda rows: any(r['topic'] == 'payment.succeeded' for r in rows))
            self.assertTrue(all(r['trip_id'] == trip['id'] for r in notices))

    def test_F07_idempotency_and_conflicting_payload(self):
        passenger = self.register()
        key = uid()
        first = self.request(passenger, key=key)
        second = self.request(passenger, key=key)
        self.assertEqual(first['id'], second['id'])
        self.expect_error(409, lambda: self.request(passenger, 'decline', key=key))
        self.assertEqual(1, len(self.api('trip', '/trips', user=passenger)['trips']))

    def test_F08_fare_is_server_calculated(self):
        passenger = self.register()
        trip = self.request(passenger)
        self.assertEqual(12000 + round(distance(self.location, self.destination) * 8000), trip['fare'])
        self.assertIsInstance(trip['fare'], int)

    def test_F09_declined_payment_compensates(self):
        driver, passenger, trip = self.offered('decline')
        self.finish(driver, trip)
        self.trip_state(passenger, trip['id'], {'payment_failed'})
        self.available(driver)
        payments = self.api('payment', '/payments', user=passenger)['payments']
        self.assertEqual(['declined'], [p['state'] for p in payments])

    def test_F10_passenger_cancel(self):
        driver, passenger, trip = self.offered()
        self.action(trip, 'cancel', passenger)
        self.available(driver)
        self.trip_state(passenger, trip['id'], {'cancelled'})

    def test_C01_two_passengers_one_driver(self):
        driver = self.driver()
        passengers = [self.register(), self.register()]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            trips = list(pool.map(self.request, passengers))
        final = [self.trip_state(p, t['id'], {'offered', 'cancelled'}) for p, t in zip(passengers, trips)]
        self.assertEqual(['cancelled', 'offered'], sorted(t['state'] for t in final))
        offered = next(t for t in final if t['state'] == 'offered')
        self.assertEqual(driver['id'], offered['driver_id'])
        profile = self.api('driver', '/drivers/me', user=driver)
        self.assertEqual(offered['id'], profile['active_trip'])

    def test_C02_concurrent_accept_and_reject(self):
        driver, passenger, trip = self.offered()

        def execute(action):
            try:
                return self.action(trip, action, driver)['state']
            except Problem as e:
                return e.status

        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(execute, ['accept', 'reject']))
        self.assertEqual(1, results.count(409))
        actual = self.api('trip', '/trips/' + trip['id'], user=passenger)
        self.assertIn(actual['state'], ('accepted', 'cancelled'))
        self.assertEqual(trip['version'] + 1, actual['version'])

    def test_C03_concurrent_idempotent_requests(self):
        passenger = self.register()
        key = uid()
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            results = list(pool.map(lambda _: self.request(passenger, key=key), range(8)))
        self.assertEqual(1, len({t['id'] for t in results}))

    def test_R01_payment_crash_and_queue_recovery(self):
        driver, passenger, trip = self.offered()
        self.cluster.stop('payment')
        try:
            self.finish(driver, trip)
            pending = self.trip_state(passenger, trip['id'], {'awaiting_payment'})
            self.assertEqual('awaiting_payment', pending['state'])
            self.wait(lambda: self.api('broker', '/stats', internal=True)['queues'],
                      lambda rows: any(r['queue'] == 'payment' and r['state'] == 'pending' for r in rows))
        finally:
            self.cluster.start('payment')
        self.trip_state(passenger, trip['id'], {'completed'})
        self.available(driver)

    def test_R02_broker_crash_outbox_and_durable_restart(self):
        driver, passenger = self.driver(), self.register()
        self.cluster.stop('broker')
        try:
            trip = self.request(passenger)
            time.sleep(.5)
            self.assertEqual('requested', self.api('trip', '/trips/' + trip['id'], user=passenger)['state'])
        finally:
            self.cluster.start('broker')
        offered = self.trip_state(passenger, trip['id'], {'offered'})
        self.assertEqual(driver['id'], offered['driver_id'])
        self.finish(driver, offered)
        self.trip_state(passenger, trip['id'], {'completed'})

    def test_R03_bounded_retry_dlq_and_redrive(self):
        driver, passenger = self.driver(), self.register()
        self.cluster.stop('driver')
        try:
            trip = self.request(passenger)
            dead = self.wait(lambda: self.api('broker', '/dead-letters', internal=True)['messages'],
                             lambda rows: any(r['queue'] == 'matching' for r in rows), seconds=25)
            delivery = next(r for r in dead if r['queue'] == 'matching')
            self.assertEqual(3, delivery['attempts'])
            metrics=self.api('matching','/internal/metrics',internal=True)
            self.assertTrue(any(c['failures']>=3 for c in metrics['circuits']))
        finally:
            self.cluster.start('driver')
        self.api('broker', '/queues/matching/redrive', 'POST', {'event_id': delivery['event_id']}, internal=True)
        offered = self.trip_state(passenger, trip['id'], {'offered'})
        self.finish(driver, offered)
        self.trip_state(passenger, trip['id'], {'completed'})

    def test_R04_reordered_cancel_before_reserve(self):
        driver = self.driver()
        trip_id = uid()
        event = dict(id=uid(), topic='trip.cancelled', producer='trip', timestamp=time.time(),
                     correlation_id=uid(), payload={'trip_id': trip_id})
        self.api('broker', '/events', 'POST', event, internal=True)
        self.wait(lambda: self.api('broker', '/queues/driver/' + event['id'], internal=True),
                  lambda d: d['state'] == 'done')
        reserved = self.api('driver', '/internal/reserve', 'POST',
                            {'trip_id': trip_id, 'pickup': self.location}, internal=True)
        self.assertIsNone(reserved['driver_id'])
        self.assertEqual('available', self.api('driver', '/drivers/me', user=driver)['status'])

    def test_F11_duplicate_event_published_once(self):
        passenger = self.register()
        event = dict(id=uid(), topic='trip.accepted', producer='trip', timestamp=time.time(),
                     correlation_id=uid(), payload={'trip_id': uid(), 'passenger_id': passenger['id']})
        first = self.api('broker', '/events', 'POST', event, internal=True)
        second = self.api('broker', '/events', 'POST', event, internal=True)
        self.assertFalse(first['duplicate'])
        self.assertTrue(second['duplicate'])
        self.wait(lambda: self.api('broker', '/queues/notification/' + event['id'], internal=True),
                  lambda d: d['state'] == 'done')
        notices = self.api('notification', '/notifications', user=passenger)['notifications']
        self.assertEqual(1, len(notices))
        changed = {**event, 'payload': {'trip_id': uid()}}
        self.expect_error(409, lambda: self.api('broker', '/events', 'POST', changed, internal=True))

    def test_R05_expired_lease_and_broker_restart(self):
        self.cluster.stop('notification')
        try:
            # Drain any previous notifications using the consumer before this scene.
            event = dict(id=uid(), topic='trip.accepted', producer='trip', timestamp=time.time(),
                         correlation_id=uid(), payload={'trip_id': uid()})
            self.api('broker', '/events', 'POST', event, internal=True)
            # Claim/ack older pending deliveries until the target is reached.
            while True:
                delivery = self.api('broker', '/queues/notification/claim', 'POST', {}, internal=True)
                if delivery.get('event') and delivery['event']['id'] == event['id']:
                    break
                if delivery.get('event'):
                    self.api('broker', '/queues/notification/ack', 'POST',
                             {'event_id': delivery['event']['id'], 'receipt': delivery['receipt']}, internal=True)
                else:
                    time.sleep(.1)
            self.cluster.stop('broker')
            self.cluster.start('broker')
            time.sleep(2.1)
            reclaimed = self.api('broker', '/queues/notification/claim', 'POST', {}, internal=True)
            self.assertEqual(event['id'], reclaimed['event']['id'])
            self.assertNotEqual(delivery['receipt'], reclaimed['receipt'])
            self.expect_error(409, lambda: self.api('broker', '/queues/notification/ack', 'POST',
                                                    {'event_id': event['id'], 'receipt': delivery['receipt']}, internal=True))
            self.api('broker', '/queues/notification/ack', 'POST',
                     {'event_id': event['id'], 'receipt': reclaimed['receipt']}, internal=True)
        finally:
            self.cluster.start('notification')

    def test_R06_saga_timeout_and_late_matching(self):
        driver, passenger = self.driver(), self.register()
        self.cluster.stop('matching')
        self.cluster.stop('trip')
        self.cluster.env['SAGA_TIMEOUT'] = '1'
        self.cluster.start('trip')
        try:
            trip = self.request(passenger)
            self.trip_state(passenger, trip['id'], {'cancelled'})
            self.wait(lambda: self.api('broker', '/stats', internal=True)['queues'],
                      lambda rows: any(r['queue'] == 'driver' and r['state'] == 'done' for r in rows))
            self.cluster.start('matching')
            self.wait(lambda: self.api('broker', '/stats', internal=True)['queues'],
                      lambda rows: not any(r['queue'] == 'matching' and r['state'] in ('pending', 'inflight') for r in rows))
            self.available(driver)
            self.assertEqual('cancelled', self.api('trip', '/trips/' + trip['id'], user=passenger)['state'])
        finally:
            self.cluster.env['SAGA_TIMEOUT'] = '300'
            self.cluster.stop('trip')
            self.cluster.start('trip')
            self.cluster.start('matching')

    def test_S01_authentication_and_resource_authorization(self):
        driver, passenger, trip = self.offered()
        stranger = self.register()
        self.expect_error(401, lambda: self.api('trip', '/trips'))
        self.expect_error(403, lambda: self.api('trip', '/trips/' + trip['id'], user=stranger))
        self.expect_error(403, lambda: self.api('driver', '/drivers/me', 'POST',
                                              {'location': self.location, 'status': 'available'}, passenger))
        self.expect_error(403, lambda: self.api('broker', '/stats'))

    def test_S02_invalid_inputs_and_password(self):
        passenger = self.register()
        self.expect_error(400, lambda: self.api('trip', '/trips', 'POST',
                                              {'pickup': [91, 0], 'destination': [0, 0]}, passenger, uid()))
        self.expect_error(400, lambda: self.api('trip', '/trips', 'POST',
                                              {'pickup': [True, 0], 'destination': [0, 0]}, passenger, uid()))
        self.expect_error(401, lambda: self.api('identity', '/login', 'POST',
                                              {'username': passenger['username'], 'password': 'wrong-password'}))
        self.expect_error(400, lambda: self.api('identity', '/register', 'POST',
                                              {'username': 'bad-admin', 'password': 'LongPassword!', 'role': 'admin'}))
        self.expect_error(413, lambda: self.api('identity', '/login', 'POST', {'padding': 'a' * 66000}))

    def test_S03_forged_token_and_lifecycle_order(self):
        driver, passenger, trip = self.offered()
        forged = {**passenger, 'token': passenger['token'][:-1] + ('0' if passenger['token'][-1] != '0' else '1')}
        self.expect_error(401, lambda: self.api('trip', '/trips', user=forged))
        self.expect_error(409, lambda: self.action(trip, 'complete', driver))

    def test_Z01_performance_concurrent_reads(self):
        passenger = self.register()
        latencies = []

        def read(_):
            start = time.perf_counter()
            self.api('trip', '/trips', user=passenger)
            return (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(10) as pool:
            latencies = list(pool.map(read, range(100)))
        duration = time.perf_counter() - start
        latencies.sort()
        metrics = dict(experiment='GET /trips over HTTP; 100 requests; 10 clients', requests=100,
                       concurrency=10, success_rate=1.0, duration_seconds=round(duration, 3),
                       throughput_rps=round(100 / duration, 2), p50_ms=round(latencies[49], 2),
                       p95_ms=round(latencies[94], 2), max_ms=round(latencies[-1], 2),
                       scope='Local processes; authenticated reads only; not booking throughput')
        (ROOT / 'docs' / 'performance.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
        self.assertEqual(100, len(latencies))


if __name__ == '__main__':
    unittest.main(verbosity=2)
