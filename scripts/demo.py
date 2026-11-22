"""Self-contained, repeatable demonstration with visible concurrency and live crashes."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.test_system import SystemTests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pause', action='store_true', help='Pause between scenes for a live presentation')
    args = parser.parse_args()
    scenes = [
        ('Normal booking: driver available, matching, accept, start, complete, payment', 'test_F03_complete_ride_and_payment'),
        ('Two concurrent passengers compete for one driver', 'test_C01_two_passengers_one_driver'),
        ('Payment process killed; persistent queue; restart and continue', 'test_R01_payment_crash_and_queue_recovery'),
        ('Broker killed; outbox retains the event; restart and publish', 'test_R02_broker_crash_outbox_and_durable_restart'),
        ('Driver service killed; bounded retry; dead letter; restart and redrive', 'test_R03_bounded_retry_dlq_and_redrive'),
        ('Payment declined; Saga compensates by releasing the driver', 'test_F09_declined_payment_compensates'),
    ]
    SystemTests.setUpClass()
    started = time.perf_counter()
    try:
        for label, method in scenes:
            if args.pause:
                input('\nPress Enter for: ' + label + '\n')
            print('\nSCENE: ' + label, flush=True)
            test = SystemTests(method)
            test.setUp()
            getattr(test, method)()
            print('PASS: ' + label, flush=True)
        print(json.dumps({'scenes': len(scenes), 'seconds': round(time.perf_counter()-started, 2),
                          'logs': str(SystemTests.run_dir / 'logs')}, indent=2))
    finally:
        SystemTests.tearDownClass()


if __name__ == '__main__':
    main()
