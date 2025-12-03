from scrapy import signals
from itemadapter import ItemAdapter
import logging
import random
import os
from itertools import cycle


class AlkotekaParserSpiderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    async def process_start(self, start):
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class AlkotekaParserDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class RegionMiddleware:
    def __init__(self, crawler):
        self.region = crawler.settings.get('REGION_NAME', 'krasnodar').lower()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"RegionMiddleware initialized with region: {self.region}")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request, spider):
        self._set_region_cookie(request)
        self._set_region_headers(request)
        self.logger.debug(f"Region middleware applied to {request.url}")
        return None

    def _set_region_cookie(self, request):
        if 'cookies' not in request.meta:
            request.meta['cookies'] = {}

        region_cookies = {
            'city': self.region,
            'selected_region': self.region,
        }

        for key, value in region_cookies.items():
            if key not in request.cookies:
                request.cookies[key] = value

    def _set_region_headers(self, request):
        region_headers = {
            'X-Region': self.region.capitalize(),
            'X-City': self.region.capitalize(),
        }

        for key, value in region_headers.items():
            if key not in request.headers:
                request.headers[key] = value

    def get_region(self):
        return self.region


class ProxyMiddleware:
    def __init__(self, crawler):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enabled = crawler.settings.get('PROXY_ENABLED', False)
        self.proxy_file = crawler.settings.get('PROXY_FILE', 'proxies.txt')
        self.proxies = []
        self.proxy_pool = None
        self.blacklist = set()
        self.stats = {'total': 0, 'success': 0, 'failed': 0}

        if self.enabled:
            self._load_proxies()
            if self.proxies:
                self.proxy_pool = cycle(self.proxies)
                self.logger.info(f"ProxyMiddleware initialized with {len(self.proxies)} proxies")
            else:
                self.logger.warning("ProxyMiddleware enabled but no proxies found")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def _load_proxies(self):
        try:
            if os.path.exists(self.proxy_file):
                with open(self.proxy_file, 'r') as f:
                    lines = f.readlines()
                    self.proxies = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
                    self.logger.info(f"Loaded {len(self.proxies)} proxies from {self.proxy_file}")
            else:
                self.logger.warning(f"Proxy file not found: {self.proxy_file}")
        except Exception as e:
            self.logger.error(f"Error loading proxies: {e}")

    def process_request(self, request, spider):
        if not self.enabled or not self.proxies:
            return None

        proxy = self._get_next_proxy()
        if proxy:
            request.meta['proxy'] = proxy
            request.meta['proxy_current'] = proxy
            self.stats['total'] += 1
            self.logger.debug(f"Using proxy {proxy} for {request.url}")

        return None

    def process_response(self, request, response, spider):
        proxy = request.meta.get('proxy_current')
        if proxy:
            self.stats['success'] += 1
            if proxy in self.blacklist:
                self.blacklist.discard(proxy)
                self.logger.info(f"Proxy {proxy} recovered (removed from blacklist)")

        return response

    def process_exception(self, request, exception, spider):
        proxy = request.meta.get('proxy_current')
        if proxy:
            self.blacklist.add(proxy)
            self.stats['failed'] += 1
            self.logger.warning(f"Proxy {proxy} failed (added to blacklist): {exception.__class__.__name__}")

            if len(self.blacklist) < len(self.proxies):
                retry_request = request.copy()
                retry_request.dont_obey_robotstxt = True
                return retry_request

    def _get_next_proxy(self):
        if not self.proxy_pool:
            return None

        attempts = 0
        while attempts < len(self.proxies):
            proxy = next(self.proxy_pool)
            if proxy not in self.blacklist:
                return proxy
            attempts += 1

        return None

    def get_stats(self):
        return {
            'total_requests': self.stats['total'],
            'successful': self.stats['success'],
            'failed': self.stats['failed'],
            'blacklisted_proxies': len(self.blacklist),
            'available_proxies': len(self.proxies) - len(self.blacklist)
        }
