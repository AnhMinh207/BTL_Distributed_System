"""Local multi-process runner. No dependency installation is needed."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common import PORTS


def environment():
    env = os.environ.copy()
    config = ROOT / '.env'
    if config.exists():
        for line in config.read_text(encoding='utf-8').splitlines():
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env.setdefault(key, value)
    env['PYTHONUNBUFFERED'] = '1'
    return env


class Cluster:
    def __init__(self, env=None, log_dir=None):
        self.env = env or environment()
        self.log_dir = Path(log_dir or ROOT / 'runtime' / 'logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.processes = {}

    def start(self, name):
        if name in self.processes and self.processes[name].poll() is None:
            return
        output = (self.log_dir / (name + '.jsonl')).open('ab')
        try:
            process = subprocess.Popen([sys.executable, '-m', 'src.main', name], cwd=ROOT,
                                       env=self.env, stdout=output, stderr=subprocess.STDOUT)
        finally:
            output.close()
        self.processes[name] = process
        deadline = time.monotonic() + 15
        port = self.env.get(name.upper() + '_URL', f'http://127.0.0.1:{PORTS[name]}')
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'{name} exited; inspect {self.log_dir / (name + ".jsonl")}')
            try:
                with urlopen(port + '/health', timeout=.5) as response:
                    if json.load(response)['service'] == name:
                        print(f'{name}: ready (PID {process.pid})', flush=True)
                        return
            except OSError:
                time.sleep(.1)
        raise RuntimeError(f'{name} did not become healthy')

    def stop(self, name):
        process = self.processes.get(name)
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=10)

    def start_all(self):
        for name in PORTS:
            self.start(name)

    def close(self):
        for name in reversed(list(self.processes)):
            self.stop(name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--services', nargs='+', choices=list(PORTS), default=list(PORTS))
    args = parser.parse_args()
    cluster = Cluster()
    try:
        for name in args.services:
            cluster.start(name)
        print('Services running. Ctrl+C to stop. Logs: runtime/logs/*.jsonl', flush=True)
        while True:
            time.sleep(1)
            failed = [name for name, p in cluster.processes.items() if p.poll() is not None]
            if failed:
                raise RuntimeError('Unexpectedly stopped services: ' + ', '.join(failed))
    except KeyboardInterrupt:
        pass
    finally:
        cluster.close()


if __name__ == '__main__':
    main()
