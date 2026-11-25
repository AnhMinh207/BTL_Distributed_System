"""Bounded Photon lookup. Public demo use: cached, serialized and throttled.

Docs: https://github.com/komoot/photon/blob/master/docs/api-v1.md
Only the configured provider URL is used; clients cannot choose an upstream URL.
"""
from collections import OrderedDict
import json
import math
import os
import threading
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from src.common import Problem, require


class Geocoder:
    def __init__(self):
        self.cache = OrderedDict()
        self.lock = threading.Lock()
        self.last_request = 0

    def search(self, query, lat='10.7769', lon='106.7009'):
        require(isinstance(query, str), 400, 'Invalid address query')
        query = ' '.join(query.split())
        require(2 <= len(query) <= 160 and not any(ord(c) < 32 for c in query), 400, 'Invalid address query')
        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            raise Problem(400, 'Invalid search location')
        require(math.isfinite(lat) and math.isfinite(lon) and abs(lat) <= 90 and abs(lon) <= 180,
                400, 'Invalid search location')
        key = (query.casefold(), round(lat, 2), round(lon, 2))
        require(self.lock.acquire(blocking=False), 429, 'Address search busy; try again shortly')
        try:
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                self.cache.move_to_end(key)
                return {**cached[1], 'cached': True}
            require(time.monotonic() - self.last_request >= 1, 429, 'Address search busy; try again shortly')
            self.last_request = time.monotonic()
            provider = os.getenv('GEOCODER_URL', 'https://photon.komoot.io/api/').rstrip('?')
            require(urlsplit(provider).scheme in ('http', 'https') and not urlsplit(provider).query,
                    503, 'Address provider is not configured correctly')
            url = provider + '?' + urlencode({'q': query, 'lat': lat, 'lon': lon, 'limit': 8})
            try:
                request = Request(url, headers={'User-Agent': 'GoRide-DS03/1.0 (educational ride booking demo)',
                                               'Accept': 'application/json'})
                with urlopen(request, timeout=4) as response:
                    raw = response.read(262145)
                require(len(raw) <= 262144, 503, 'Address provider response too large')
                data = json.loads(raw)
            except Problem:
                raise
            except Exception as e:
                raise Problem(503, 'Address search unavailable; use a saved place or coordinates') from e
            result = {'places': self.normalize(data), 'provider': 'Photon',
                      'attribution': '© OpenStreetMap contributors', 'cached': False}
            self.cache[key] = (time.monotonic() + 900, result)
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
            return result
        finally:
            self.lock.release()

    @staticmethod
    def normalize(data):
        require(isinstance(data, dict) and isinstance(data.get('features'), list), 503, 'Invalid address provider response')
        places, seen = [], set()
        for feature in data['features'][:20]:
            try:
                if feature['geometry']['type'] != 'Point':
                    continue
                lon, lat = feature['geometry']['coordinates']
                if type(lat) not in (int, float) or type(lon) not in (int, float) or not math.isfinite(lat) or not math.isfinite(lon) or abs(lat) > 90 or abs(lon) > 180:
                    continue
                p = feature['properties']
                def field(key):
                    value = p.get(key)
                    return str(value).strip()[:200] if isinstance(value, (str, int)) else ''
                street = ' '.join(filter(None, [field('housenumber'), field('street')]))
                name = field('name') or street or field('city') or field('district')
                if not name:
                    continue
                address = ', '.join(dict.fromkeys(v for v in [street, field('district'), field('city'), field('state'), field('country')] if v and v != name))
                key = (name, round(lat, 6), round(lon, 6))
                if key in seen:
                    continue
                seen.add(key)
                places.append({'name': name, 'address': address, 'location': [lat, lon],
                               'area': field('city') or field('state') or field('country'), 'source': 'OpenStreetMap'})
                if len(places) == 8:
                    break
            except (KeyError, TypeError, ValueError):
                continue
        return places
