"""Reproducible advanced demonstrations; no access to business DBs."""
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.test_advanced import AdvancedTests

scenes=[('Circuit breaker: closed -> open -> half-open -> closed','test_A01_circuit_open_half_open_and_recovery'),
        ('Demand/supply pricing and stable quote replay','test_A02_dynamic_pricing_and_idempotent_quote'),
        ('Cross-service parent/child spans and central logs','test_A03_central_logs_and_parent_child_trace'),
        ('Two Matching instances; kill one; survivor keeps processing','test_A04_two_matching_replicas_and_crash_recovery'),
        ('Pricing restart; replay creates no duplicate booking','test_A05_pricing_restart_and_no_duplicate_booking'),
        ('Geospatial matching selects the nearest driver','test_A06_geospatial_selects_nearest_driver')]

if __name__=='__main__':
    AdvancedTests.setUpClass()
    try:
        for label,name in scenes:
            if '--pause' in sys.argv:input('\nEnter: '+label+'\n')
            print('\nSCENE: '+label,flush=True)
            test=AdvancedTests(name);test.setUp();getattr(test,name)()
            print('PASS: '+label,flush=True)
    finally:AdvancedTests.tearDownClass()
