import argparse
import os


def main():
    parser = argparse.ArgumentParser(description='DS03 independently deployed services')
    parser.add_argument('service', choices=['broker', 'identity', 'driver', 'trip', 'matching', 'payment', 'notification'])
    args = parser.parse_args()
    for name in ('AUTH_SECRET', 'SERVICE_KEY'):
        if len(os.getenv(name, '')) < 32:
            parser.error(f'{name} must contain at least 32 characters; run scripts/configure.py')
    from .broker import Broker
    from .identity import Identity
    from .driver import Driver
    from .trip import Trip
    from .matching import Matching
    from .payment import Payment
    from .notification import Notification
    services = dict(broker=Broker, identity=Identity, driver=Driver, trip=Trip,
                    matching=Matching, payment=Payment, notification=Notification)
    services[args.service]().run()


if __name__ == '__main__':
    main()
