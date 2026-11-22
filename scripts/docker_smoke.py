"""Validate an already-running Compose stack over public HTTP, including crashes.

Run after Compose up. Only the explicitly named project is operated on.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cluster import environment
from src.common import PORTS, call
from tests.test_system import SystemTests


class DockerCluster:
    def __init__(self, project, urls):
        self.project = project
        self.urls = urls

    def command(self, action, name):
        subprocess.run(['docker', 'compose', '--project-name', self.project, '--env-file', str(ROOT / '.env'),
                        '-f', str(ROOT / 'deploy' / 'compose.yaml'), action, name],
                       check=True, cwd=ROOT, timeout=45)

    def stop(self, name):
        self.command('kill', name)

    def start(self, name):
        self.command('start', name)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                call(self.urls[name] + '/health', timeout=1)
                return
            except Exception:
                time.sleep(.2)
        raise RuntimeError('Container did not recover: ' + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', default='ds03-validation')
    args = parser.parse_args()
    env = environment()
    SystemTests.env = env
    SystemTests.urls = {n: env.get(n.upper() + '_URL', f'http://127.0.0.1:{p}') for n, p in PORTS.items()}
    SystemTests.cluster = DockerCluster(args.project, SystemTests.urls)
    names = ['test_F03_complete_ride_and_payment', 'test_C01_two_passengers_one_driver',
             'test_R01_payment_crash_and_queue_recovery', 'test_R02_broker_crash_outbox_and_durable_restart',
             'test_F09_declined_payment_compensates', 'test_S01_authentication_and_resource_authorization',
             'test_S02_invalid_inputs_and_password', 'test_F11_duplicate_event_published_once']
    records = []
    for name in names:
        test = SystemTests(name)
        test.setUp()
        started = time.perf_counter()
        try:
            getattr(test, name)()
            records.append(dict(test=name, status='passed', seconds=round(time.perf_counter()-started, 3)))
            print('PASS Docker: ' + name, flush=True)
        except Exception as e:
            records.append(dict(test=name, status='failed', error=str(e)))
            raise
        finally:
            (ROOT / 'docs' / 'docker-results.json').write_text(
                json.dumps({'project': args.project, 'tests': records,
                            'scope': '8 selected HTTP scenarios on Compose; not the complete 24-test local suite'},
                           indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
