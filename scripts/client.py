"""Command-line UI for the passenger, driver and operator."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cluster import environment
from src.common import Problem, call, service_url, uid, PORTS


def main():
    os.environ.update(environment())
    parser = argparse.ArgumentParser(description='DS03 CLI (JSON output; keep tokens private)')
    parser.add_argument('command', choices=['register', 'login', 'status', 'driver', 'request', 'trips',
                                          'trip', 'accept', 'reject', 'start', 'complete', 'cancel',
                                          'notifications', 'payments', 'queues', 'dead-letters', 'redrive'])
    parser.add_argument('--username')
    parser.add_argument('--role', choices=['passenger', 'driver'], default='passenger')
    parser.add_argument('--token', default=os.getenv('DS03_TOKEN'))
    parser.add_argument('--location', nargs=2, type=float, default=[10.7769, 106.7009])
    parser.add_argument('--destination', nargs=2, type=float, default=[10.7900, 106.7200])
    parser.add_argument('--status', choices=['available', 'offline', 'busy'], default='available')
    parser.add_argument('--payment-mode', choices=['success', 'decline'], default='success')
    parser.add_argument('--trip-id')
    parser.add_argument('--version', type=int)
    parser.add_argument('--key', default=uid())
    parser.add_argument('--queue', default='matching')
    parser.add_argument('--event-id')
    args = parser.parse_args()
    headers = {'Authorization': 'Bearer ' + args.token} if args.token else {}
    method, data = 'GET', None
    command = args.command
    if command in ('register', 'login'):
        import getpass
        password = getpass.getpass('Password (at least 10 characters): ')
        service, path, method = 'identity', '/' + command, 'POST'
        data = dict(username=args.username, password=password, role=args.role)
    elif command == 'status':
        results = {}
        for name in PORTS:
            try:
                results[name] = call(service_url(name) + '/health')[1]
            except Problem as e:
                results[name] = {'status': 'down', 'error': e.message}
        print(json.dumps(results, indent=2))
        return
    elif command == 'driver':
        service, path, method = 'driver', '/drivers/me', 'POST'
        data = dict(location=args.location, status=args.status)
    elif command == 'request':
        service, path, method = 'trip', '/trips', 'POST'
        data = dict(pickup=args.location, destination=args.destination, payment_mode=args.payment_mode)
        headers['Idempotency-Key'] = args.key
    elif command in ('trips', 'trip'):
        service, path = 'trip', '/trips' + ('/' + str(args.trip_id) if command == 'trip' else '')
    elif command in ('accept', 'reject', 'start', 'complete', 'cancel'):
        service, path, method = 'trip', '/trips/' + str(args.trip_id) + '/' + command, 'POST'
        data = {'version': args.version}
    elif command in ('notifications', 'payments'):
        service, path = ('notification' if command == 'notifications' else 'payment'), '/' + command
    else:
        service = 'broker'
        headers = {'X-Service-Key': os.environ['SERVICE_KEY']}
        path = '/stats' if command == 'queues' else '/dead-letters'
        if command == 'redrive':
            path, method = '/queues/' + args.queue + '/redrive', 'POST'
            data = {'event_id': args.event_id}
    try:
        _, result = call(service_url(service) + path, method, data, headers)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Problem as e:
        print(json.dumps({'status': e.status, 'error': e.message}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
