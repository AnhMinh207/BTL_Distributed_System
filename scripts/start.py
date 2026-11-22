"""One command for the web application and missing business services.

Existing healthy services are reused. Only owned child processes are stopped on exit.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cluster import Cluster, environment
from src.common import PORTS, Problem, call


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--open', action='store_true', help='Open the app in the default browser')
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'configure.py')], check=True)
    env = environment()
    cluster = Cluster(env)
    web_process = None
    url = 'http://127.0.0.1:' + env.get('WEB_PORT', '8080')
    try:
        for name, port in PORTS.items():
            try:
                _, health = call(env.get(name.upper() + '_URL', f'http://127.0.0.1:{port}') + '/health', timeout=.5)
                if health.get('service') != name:
                    raise RuntimeError(f'Port for {name} is occupied by another application')
                print(name + ': reusing running service', flush=True)
            except Problem:
                cluster.start(name)
        try:
            _, health = call(url + '/health', timeout=.5)
            if health.get('service') != 'web':
                raise RuntimeError('Web port is occupied by another application')
        except Problem:
            with (cluster.log_dir / 'web.jsonl').open('ab') as output:
                web_process = subprocess.Popen([sys.executable, str(ROOT / 'scripts' / 'web.py')],
                                               cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 15
            while True:
                if web_process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Web startup failed; inspect runtime/logs/web.jsonl')
                try:
                    call(url + '/health', timeout=.5)
                    break
                except Problem:
                    time.sleep(.15)
        print('\nOPEN IN YOUR BROWSER: ' + url, flush=True)
        print('Select "Chuan bi demo" to create passenger/driver accounts. Ctrl+C to stop.', flush=True)
        if args.open:
            webbrowser.open(url)
        while True:
            time.sleep(1)
            if web_process and web_process.poll() is not None:
                raise RuntimeError('Web process stopped unexpectedly')
            for name, process in cluster.processes.items():
                if process.poll() is not None:
                    raise RuntimeError(name + ' stopped unexpectedly; inspect runtime/logs')
    except KeyboardInterrupt:
        pass
    finally:
        if web_process and web_process.poll() is None:
            web_process.terminate()
            web_process.wait(timeout=10)
        cluster.close()


if __name__ == '__main__':
    main()
