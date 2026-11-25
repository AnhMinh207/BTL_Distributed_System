"""Provider boundary tests; independent from public network availability."""
import json
import unittest
from unittest.mock import patch
from io import BytesIO

from scripts.geocoding import Geocoder
from src.common import Problem


class GeocodingTests(unittest.TestCase):
    def fixture(self):
        return {'features': [{'geometry': {'type': 'Point', 'coordinates': [105.85, 21.03]},
                              'properties': {'name': 'A place', 'housenumber': '12',
                                             'street': 'Example street', 'city': 'Ha Noi', 'country': 'Viet Nam'}}]}

    def test_coordinates_and_address_are_normalized(self):
        result = Geocoder.normalize(self.fixture())
        self.assertEqual([21.03, 105.85], result[0]['location'])
        self.assertIn('12 Example street', result[0]['address'])

    def test_bad_geometry_and_duplicates_are_rejected(self):
        data = self.fixture()
        data['features'] *= 2
        data['features'].append({'geometry': {'type': 'Point', 'coordinates': [1000, 20]}, 'properties': {'name': 'bad'}})
        data['features'].append({'geometry': {'type': 'Point', 'coordinates': [True, 20]}, 'properties': {'name': 'bad'}})
        data['features'].append({})
        self.assertEqual(1, len(Geocoder.normalize(data)))

    @patch('scripts.geocoding.urlopen')
    def test_same_query_is_cached_and_not_sent_again(self, upstream):
        upstream.return_value = BytesIO(json.dumps(self.fixture()).encode())
        geocoder = Geocoder()
        first = geocoder.search('Example place')
        second = geocoder.search('Example place')
        self.assertFalse(first['cached'])
        self.assertTrue(second['cached'])
        self.assertEqual(1, upstream.call_count)

    @patch('scripts.geocoding.urlopen')
    def test_uncached_requests_are_throttled(self, upstream):
        upstream.return_value = BytesIO(json.dumps(self.fixture()).encode())
        geocoder = Geocoder()
        geocoder.search('First place')
        with self.assertRaises(Problem) as e:
            geocoder.search('Second place')
        self.assertEqual(429, e.exception.status)

    def test_validation_happens_before_any_network(self):
        for query, lat, lon in [('', 10, 106), ('x'*161, 10, 106), ('place', 'nan', 106), ('place', 91, 106), ('place', 10, 181)]:
            with self.assertRaises(Problem) as e:
                Geocoder().search(query, lat, lon)
            self.assertEqual(400, e.exception.status)

    @patch('scripts.geocoding.urlopen', side_effect=TimeoutError)
    def test_provider_failure_is_actionable(self, upstream):
        with self.assertRaises(Problem) as e:
            Geocoder().search('Example place')
        self.assertEqual(503, e.exception.status)


if __name__ == '__main__':
    unittest.main(verbosity=2)
