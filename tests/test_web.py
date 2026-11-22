"""Public gateway integration: real requests through web to independent services."""
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.common import call, Problem, uid
from tests.test_system import SystemTests


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        SystemTests.setUpClass()
        cls.url='http://127.0.0.1:9180'
        with (SystemTests.run_dir/'logs'/'web.jsonl').open('ab') as output:
            cls.process=subprocess.Popen([sys.executable,'scripts/web.py','--port','9180'],cwd=ROOT,
                                         env=SystemTests.env,stdout=output,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                try:
                    call(cls.url+'/health',timeout=.5)
                    return
                except Problem:
                    time.sleep(.1)
            raise RuntimeError('Web gateway did not become healthy')
        except BaseException:
            cls.process.kill();cls.process.wait();SystemTests.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.process.kill();cls.process.wait(timeout=10);SystemTests.tearDownClass()

    def request(self,service,path,method='GET',data=None,user=None,extra=None):
        headers={'Authorization':'Bearer '+user['token']} if user else {}
        headers.update(extra or {})
        return call(self.url+'/api/'+service+path,method,data,headers)[1]

    def register(self,role):
        return self.request('identity','/register','POST',
                            {'username':role+uid()[:10],'password':'Web-test-pass-2026!','role':role})

    def wait_trip(self,user,trip_id,expected):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            trip=self.request('trip','/trips/'+trip_id,user=user)
            if trip['state']==expected:return trip
            time.sleep(.15)
        self.fail('Trip did not reach '+expected)

    def test_W01_static_assets_and_security_headers(self):
        for path,mime in [('/','text/html'),('/app.js','text/javascript'),('/styles.css','text/css'),('/favicon.svg','image/svg+xml')]:
            with urlopen(self.url+path,timeout=2) as response:
                self.assertEqual(200,response.status)
                self.assertIn(mime,response.headers['Content-Type'])
                self.assertEqual('nosniff',response.headers['X-Content-Type-Options'])
                self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])
                self.assertGreater(len(response.read()),100)

    def test_W02_privileged_proxy_routes_are_blocked(self):
        for path in ['/api/broker/stats','/api/driver/internal/reserve','/api/trip/health','/.env','/../.env']:
            with self.assertRaises(Problem) as caught:
                call(self.url+path,'POST',{}, {'X-Service-Key':SystemTests.env['SERVICE_KEY']})
            self.assertEqual(404,caught.exception.status)

    def test_W03_cross_origin_write_is_rejected(self):
        with self.assertRaises(Problem) as caught:
            self.request('identity','/register','POST',{},extra={'Origin':'https://untrusted.example'})
        self.assertEqual(403,caught.exception.status)

    def test_W04_complete_booking_through_gateway(self):
        passenger,driver=self.register('passenger'),self.register('driver')
        self.request('driver','/drivers/me','POST',{'location':[10.7769,106.7009],'status':'available'},driver)
        payload={'pickup':[10.7769,106.7009],'destination':[10.79,106.72],'payment_mode':'success'}
        key=uid()
        trip=self.request('trip','/trips','POST',payload,passenger,{'Idempotency-Key':key})
        again=self.request('trip','/trips','POST',payload,passenger,{'Idempotency-Key':key})
        self.assertEqual(trip['id'],again['id'])
        trip=self.wait_trip(passenger,trip['id'],'offered')
        self.assertEqual(driver['id'],trip['driver_id'])
        for action in ['accept','start','complete']:
            trip=self.request('trip',f'/trips/{trip["id"]}/{action}','POST',{'version':trip['version']},driver)
        self.wait_trip(passenger,trip['id'],'completed')
        self.assertEqual('paid',self.request('payment','/payments',user=passenger)['payments'][0]['state'])
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            notices=self.request('notification','/notifications',user=driver)['notifications']
            if any(n['topic']=='payment.succeeded' for n in notices):break
            time.sleep(.15)
        else:self.fail('Driver notification missing')
        stranger=self.register('passenger')
        with self.assertRaises(Problem) as caught:
            self.request('trip','/trips/'+trip['id'],user=stranger)
        self.assertEqual(403,caught.exception.status)

    def test_W05_health_aggregate(self):
        status=call(self.url+'/api/status')[1]['services']
        self.assertEqual(7,len(status))
        self.assertTrue(all(s['status']=='up' for s in status.values()))

    def test_W06_proxy_preserves_authentication_and_limits(self):
        with self.assertRaises(Problem) as caught:self.request('trip','/trips')
        self.assertEqual(401,caught.exception.status)
        with self.assertRaises(Problem) as caught:self.request('identity','/login','POST',{'padding':'x'*66000})
        self.assertEqual(413,caught.exception.status)


if __name__=='__main__':
    started=time.perf_counter()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WebTests))
    (ROOT/'docs'/'web-test-results.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),
        'errors':len(result.errors),'seconds':round(time.perf_counter()-started,3),
        'scope':'Public gateway, assets, access control, complete booking over HTTP'},indent=2),encoding='utf-8')
    sys.exit(0 if result.wasSuccessful() else 1)
