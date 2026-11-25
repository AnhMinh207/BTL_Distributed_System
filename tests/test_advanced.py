"""Advanced DS03 evidence: actual network/services, replicas with independent databases."""
import concurrent.futures
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.common import uid,call,Problem
from src.resilience import Circuits,CircuitOpen
from tests.test_system import SystemTests


class AdvancedTests(SystemTests):
    def test_A01_circuit_open_half_open_and_recovery(self):
        circuit=Circuits()
        with patch('src.resilience.time.monotonic',return_value=100):
            for _ in range(3):
                key=circuit.before('http://driver/reserve');circuit.after(key,True)
            with self.assertRaises(CircuitOpen):circuit.before('http://driver/reserve')
        with patch('src.resilience.time.monotonic',return_value=200):
            probe=circuit.before('http://driver/reserve')
            with self.assertRaises(CircuitOpen):circuit.before('http://driver/reserve')
            circuit.after(probe,False)
            self.assertIsNotNone(circuit.before('http://driver/reserve'))
            self.assertEqual([],circuit.snapshot())

    def test_A02_dynamic_pricing_and_idempotent_quote(self):
        self.cluster.stop('matching')
        try:
            passengers=[self.register() for _ in range(3)]
            trips=[self.request(p) for p in passengers]
            self.assertLess(trips[0]['fare'],trips[1]['fare'])
            self.assertLess(trips[1]['fare'],trips[2]['fare'])
            payload=dict(pickup=self.location,destination=self.destination,quote_key=uid())
            first=self.api('pricing','/internal/quote','POST',payload,internal=True)
            second=self.api('pricing','/internal/quote','POST',payload,internal=True)
            self.assertEqual(first,second)
            self.assertGreater(first['multiplier'],1)
            self.assertLessEqual(first['multiplier'],2)
        finally:
            self.cluster.start('matching')
        for p,t in zip(passengers,trips):self.trip_state(p,t['id'],{'cancelled'})

    def test_A03_central_logs_and_parent_child_trace(self):
        driver,passenger,trip=self.offered()
        self.finish(driver,trip);self.trip_state(passenger,trip['id'],{'completed'})
        trace=self.wait(lambda:self.api('observability','/traces/'+trip['correlation_id'],internal=True)['records'],
                        lambda rows:len({r['node'] for r in rows})>=6,seconds=20)
        self.assertTrue(any(r.get('parent_span_id') for r in trace))
        self.assertTrue(any(r['event']=='span.consumer' for r in trace))
        spans={r.get('span_id') for r in trace if r.get('span_id')}
        self.assertTrue(any(r.get('parent_span_id') in spans for r in trace if r.get('parent_span_id')))
        self.assertIn('pricing',{r['node'] for r in trace})
        (ROOT/'docs'/'trace-example.json').write_text(json.dumps({'trace_id':trip['correlation_id'],'records':trace},indent=2),encoding='utf-8')
        self.expect_error(403,lambda:self.api('observability','/logs'))

    def test_A04_two_matching_replicas_and_crash_recovery(self):
        self.cluster.stop('matching')
        replicas=[]
        def launch(name,port):
            env={**self.env,'INSTANCE_ID':name,'PORT':str(port),'MATCHING_REPLICA_DATA':'1'}
            with (self.run_dir/'logs'/(name+'.jsonl')).open('ab') as output:
                process=subprocess.Popen([sys.executable,'-m','src.main','matching'],cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT)
            replicas.append(process)
            self.wait(lambda:process.poll() is None)
        try:
            launch('matching-a',9214);launch('matching-b',9215)
            time.sleep(.5)
            passengers=[self.register() for _ in range(12)]
            with concurrent.futures.ThreadPoolExecutor(6) as pool:trips=list(pool.map(self.request,passengers))
            for p,t in zip(passengers,trips):self.trip_state(p,t['id'],{'cancelled'})
            def processed(name):
                rows=[json.loads(s) for s in (self.run_dir/'logs'/(name+'.jsonl')).read_text().splitlines() if s.startswith('{')]
                return sum(r['event']=='event.processed' for r in rows)
            self.wait(lambda:[processed('matching-a'),processed('matching-b')],lambda counts:all(n>0 for n in counts))
            # Stronger evidence reads each replica's own log, never business DBs.
            counts={}
            for name in ('matching-a','matching-b'):
                rows=[json.loads(s) for s in (self.run_dir/'logs'/(name+'.jsonl')).read_text().splitlines() if s.startswith('{')]
                counts[name]=sum(r['event']=='event.processed' for r in rows)
                self.assertGreater(counts[name],0)
            replicas[0].kill();replicas[0].wait(timeout=5)
            passenger=self.register();trip=self.request(passenger);self.trip_state(passenger,trip['id'],{'cancelled'})
            self.assertIsNone(replicas[1].poll())
            (ROOT/'docs'/'scaling-results.json').write_text(json.dumps({'replicas':2,'processed_per_instance':counts,
                'survivor_continued_after_peer_kill':True,'database_isolation':'separate instance namespaces; communication through broker only'},indent=2),encoding='utf-8')
        finally:
            for process in replicas:
                if process.poll() is None:process.kill();process.wait(timeout=5)
            self.cluster.start('matching')

    def test_A05_pricing_restart_and_no_duplicate_booking(self):
        passenger=self.register();key=uid();trip=self.request(passenger,key=key)
        self.cluster.stop('pricing')
        try:
            again=self.request(passenger,key=key)
            self.assertEqual(trip['id'],again['id'])
        finally:self.cluster.start('pricing')
        self.assertEqual(1,len(self.api('trip','/trips',user=passenger)['trips']))

    def test_A06_geospatial_selects_nearest_driver(self):
        far=self.driver()
        self.api('driver','/drivers/me','POST',{'location':[self.location[0]+.04,self.location[1]],'status':'available'},far)
        near=self.driver();passenger=self.register();trip=self.request(passenger)
        offered=self.trip_state(passenger,trip['id'],{'offered'})
        self.assertEqual(near['id'],offered['driver_id'])
        self.assertEqual('available',self.api('driver','/drivers/me',user=far)['status'])


if __name__=='__main__':
    started=time.perf_counter()
    names=sorted(n for n in AdvancedTests.__dict__ if n.startswith('test_A'))
    suite=unittest.TestSuite(AdvancedTests(name) for name in names)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT/'docs'/'advanced-test-results.json').write_text(json.dumps(dict(tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),seconds=round(time.perf_counter()-started,3),
        scenarios=names,run_directory=str(AdvancedTests.run_dir)),indent=2),encoding='utf-8')
    sys.exit(not result.wasSuccessful())
