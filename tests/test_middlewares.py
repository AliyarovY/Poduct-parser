import unittest
from unittest.mock import Mock, MagicMock
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'alkoteka_parser', 'alkoteka_parser'))

from middlewares import RegionMiddleware


class TestRegionMiddleware(unittest.TestCase):
    def setUp(self):
        self.mock_crawler = Mock()
        self.mock_crawler.settings.get.return_value = 'krasnodar'

    def test_initialization_with_default_region(self):
        middleware = RegionMiddleware(self.mock_crawler)
        self.assertEqual(middleware.region, 'krasnodar')

    def test_initialization_with_custom_region(self):
        self.mock_crawler.settings.get.return_value = 'moscow'
        middleware = RegionMiddleware(self.mock_crawler)
        self.assertEqual(middleware.region, 'moscow')

    def test_region_lowercase(self):
        self.mock_crawler.settings.get.return_value = 'MOSCOW'
        middleware = RegionMiddleware(self.mock_crawler)
        self.assertEqual(middleware.region, 'moscow')

    def test_get_region(self):
        middleware = RegionMiddleware(self.mock_crawler)
        self.assertEqual(middleware.get_region(), 'krasnodar')

    def test_set_region_cookie(self):
        middleware = RegionMiddleware(self.mock_crawler)
        request = Mock()
        request.meta = {}
        request.cookies = {}

        middleware._set_region_cookie(request)

        self.assertIn('city', request.cookies)
        self.assertEqual(request.cookies['city'], 'krasnodar')
        self.assertIn('selected_region', request.cookies)
        self.assertEqual(request.cookies['selected_region'], 'krasnodar')

    def test_set_region_cookie_not_override_existing(self):
        middleware = RegionMiddleware(self.mock_crawler)
        request = Mock()
        request.meta = {}
        request.cookies = {'city': 'spb'}

        middleware._set_region_cookie(request)

        self.assertEqual(request.cookies['city'], 'spb')

    def test_set_region_headers(self):
        middleware = RegionMiddleware(self.mock_crawler)
        request = Mock()
        request.headers = {}

        middleware._set_region_headers(request)

        self.assertIn('X-Region', request.headers)
        self.assertEqual(request.headers['X-Region'], 'Krasnodar')
        self.assertIn('X-City', request.headers)
        self.assertEqual(request.headers['X-City'], 'Krasnodar')

    def test_set_region_headers_capitalization(self):
        self.mock_crawler.settings.get.return_value = 'moscow'
        middleware = RegionMiddleware(self.mock_crawler)
        request = Mock()
        request.headers = {}

        middleware._set_region_headers(request)

        self.assertEqual(request.headers['X-Region'], 'Moscow')
        self.assertEqual(request.headers['X-City'], 'Moscow')

    def test_set_region_headers_not_override_existing(self):
        middleware = RegionMiddleware(self.mock_crawler)
        request = Mock()
        request.headers = {'X-Region': 'SPB'}

        middleware._set_region_headers(request)

        self.assertEqual(request.headers['X-Region'], 'SPB')

    def test_process_request_applies_both(self):
        middleware = RegionMiddleware(self.mock_crawler)
        request = Mock()
        request.meta = {}
        request.cookies = {}
        request.headers = {}
        request.url = 'https://alkoteka.com/catalog'

        result = middleware.process_request(request, None)

        self.assertIsNone(result)
        self.assertIn('city', request.cookies)
        self.assertIn('X-Region', request.headers)

    def test_from_crawler(self):
        middleware = RegionMiddleware.from_crawler(self.mock_crawler)
        self.assertIsInstance(middleware, RegionMiddleware)
        self.assertEqual(middleware.region, 'krasnodar')

    def test_multiple_requests_same_middleware(self):
        middleware = RegionMiddleware(self.mock_crawler)

        request1 = Mock()
        request1.meta = {}
        request1.cookies = {}
        request1.headers = {}

        request2 = Mock()
        request2.meta = {}
        request2.cookies = {}
        request2.headers = {}

        middleware.process_request(request1, None)
        middleware.process_request(request2, None)

        self.assertEqual(request1.cookies['city'], 'krasnodar')
        self.assertEqual(request2.cookies['city'], 'krasnodar')

    def test_region_consistency_across_requests(self):
        middleware = RegionMiddleware(self.mock_crawler)
        self.mock_crawler.settings.get.return_value = 'novosibirsk'

        new_middleware = RegionMiddleware(self.mock_crawler)
        self.assertEqual(middleware.region, 'krasnodar')
        self.assertEqual(new_middleware.region, 'novosibirsk')


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestRegionMiddleware))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    exit(0 if result.wasSuccessful() else 1)
