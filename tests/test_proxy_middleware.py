import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
import tempfile

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'alkoteka_parser', 'alkoteka_parser'))

from middlewares import ProxyMiddleware


class TestProxyMiddleware(unittest.TestCase):
    def setUp(self):
        self.mock_crawler = Mock()
        self.mock_crawler.settings.get = Mock(side_effect=self._settings_get)
        self.temp_file = None

    def _settings_get(self, key, default=None):
        settings = {
            'PROXY_ENABLED': False,
            'PROXY_FILE': 'proxies.txt',
        }
        return settings.get(key, default)

    def test_proxy_middleware_disabled(self):
        middleware = ProxyMiddleware(self.mock_crawler)
        self.assertFalse(middleware.enabled)
        self.assertEqual(len(middleware.proxies), 0)

    def test_proxy_middleware_enabled_no_file(self):
        self.mock_crawler.settings.get = Mock(side_effect=lambda k, d=None:
            True if k == 'PROXY_ENABLED' else (d if k == 'PROXY_FILE' else d))
        middleware = ProxyMiddleware(self.mock_crawler)
        self.assertTrue(middleware.enabled)
        self.assertEqual(len(middleware.proxies), 0)

    def test_load_proxies_from_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("http://10.0.0.1:8080\n")
            f.write("http://10.0.0.2:8080\n")
            f.write("# Comment line\n")
            f.write("http://10.0.0.3:8080\n")
            temp_path = f.name

        try:
            self.mock_crawler.settings.get = Mock(side_effect=lambda k, d=None:
                True if k == 'PROXY_ENABLED' else (temp_path if k == 'PROXY_FILE' else d))

            middleware = ProxyMiddleware(self.mock_crawler)
            self.assertEqual(len(middleware.proxies), 3)
            self.assertIn("http://10.0.0.1:8080", middleware.proxies)
        finally:
            os.unlink(temp_path)

    def test_process_request_disabled(self):
        middleware = ProxyMiddleware(self.mock_crawler)
        request = Mock()
        request.meta = {}

        result = middleware.process_request(request, None)

        self.assertIsNone(result)
        self.assertNotIn('proxy', request.meta)

    def test_process_request_with_proxy(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("http://10.0.0.1:8080\n")
            f.write("http://10.0.0.2:8080\n")
            temp_path = f.name

        try:
            self.mock_crawler.settings.get = Mock(side_effect=lambda k, d=None:
                True if k == 'PROXY_ENABLED' else (temp_path if k == 'PROXY_FILE' else d))

            middleware = ProxyMiddleware(self.mock_crawler)
            request = Mock()
            request.meta = {}
            request.url = "http://example.com"

            result = middleware.process_request(request, None)

            self.assertIsNone(result)
            self.assertIn('proxy', request.meta)
            self.assertIn('proxy_current', request.meta)
            self.assertEqual(middleware.stats['total'], 1)
        finally:
            os.unlink(temp_path)

    def test_proxy_rotation(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("http://10.0.0.1:8080\n")
            f.write("http://10.0.0.2:8080\n")
            f.write("http://10.0.0.3:8080\n")
            temp_path = f.name

        try:
            self.mock_crawler.settings.get = Mock(side_effect=lambda k, d=None:
                True if k == 'PROXY_ENABLED' else (temp_path if k == 'PROXY_FILE' else d))

            middleware = ProxyMiddleware(self.mock_crawler)
            used_proxies = set()

            for _ in range(6):
                request = Mock()
                request.meta = {}
                middleware.process_request(request, None)
                used_proxies.add(request.meta.get('proxy'))

            self.assertTrue(len(used_proxies) >= 2, "Proxy rotation not working")
        finally:
            os.unlink(temp_path)

    def test_process_response_success(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("http://10.0.0.1:8080\n")
            temp_path = f.name

        try:
            self.mock_crawler.settings.get = Mock(side_effect=lambda k, d=None:
                True if k == 'PROXY_ENABLED' else (temp_path if k == 'PROXY_FILE' else d))

            middleware = ProxyMiddleware(self.mock_crawler)
            request = Mock()
            request.meta = {'proxy_current': 'http://10.0.0.1:8080'}
            response = Mock()

            result = middleware.process_response(request, response, None)

            self.assertEqual(result, response)
            self.assertEqual(middleware.stats['success'], 1)
        finally:
            os.unlink(temp_path)

    def test_process_exception_blacklist(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("http://10.0.0.1:8080\n")
            f.write("http://10.0.0.2:8080\n")
            temp_path = f.name

        try:
            self.mock_crawler.settings.get = Mock(side_effect=lambda k, d=None:
                True if k == 'PROXY_ENABLED' else (temp_path if k == 'PROXY_FILE' else d))

            middleware = ProxyMiddleware(self.mock_crawler)
            request = Mock()
            request.meta = {'proxy_current': 'http://10.0.0.1:8080'}
            request.copy = Mock(return_value=request)
            exception = Exception("Connection timeout")

            result = middleware.process_exception(request, exception, None)

            self.assertIn('http://10.0.0.1:8080', middleware.blacklist)
            self.assertEqual(middleware.stats['failed'], 1)
            self.assertEqual(result, request)
        finally:
            os.unlink(temp_path)

    def test_get_stats(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("http://10.0.0.1:8080\n")
            f.write("http://10.0.0.2:8080\n")
            temp_path = f.name

        try:
            self.mock_crawler.settings.get = Mock(side_effect=lambda k, d=None:
                True if k == 'PROXY_ENABLED' else (temp_path if k == 'PROXY_FILE' else d))

            middleware = ProxyMiddleware(self.mock_crawler)
            stats = middleware.get_stats()

            self.assertIn('total_requests', stats)
            self.assertIn('successful', stats)
            self.assertIn('failed', stats)
            self.assertIn('blacklisted_proxies', stats)
            self.assertIn('available_proxies', stats)
        finally:
            os.unlink(temp_path)

    def test_from_crawler(self):
        middleware = ProxyMiddleware.from_crawler(self.mock_crawler)
        self.assertIsInstance(middleware, ProxyMiddleware)

    def test_blacklist_removal_on_success(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("http://10.0.0.1:8080\n")
            temp_path = f.name

        try:
            self.mock_crawler.settings.get = Mock(side_effect=lambda k, d=None:
                True if k == 'PROXY_ENABLED' else (temp_path if k == 'PROXY_FILE' else d))

            middleware = ProxyMiddleware(self.mock_crawler)
            proxy = 'http://10.0.0.1:8080'
            middleware.blacklist.add(proxy)

            request = Mock()
            request.meta = {'proxy_current': proxy}
            response = Mock()

            middleware.process_response(request, response, None)

            self.assertNotIn(proxy, middleware.blacklist)
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestProxyMiddleware))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    exit(0 if result.wasSuccessful() else 1)
