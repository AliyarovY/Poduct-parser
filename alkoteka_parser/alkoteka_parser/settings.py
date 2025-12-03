BOT_NAME = "alkoteka_parser"

SPIDER_MODULES = ["alkoteka_parser.spiders"]
NEWSPIDER_MODULE = "alkoteka_parser.spiders"

PROJECT_VERSION = "0.1.0"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

ROBOTSTXT_OBEY = False
ROBOTSTXT_USER_AGENT = BOT_NAME
ALLOWED_DOMAIN = "alkoteka.com"
HTTPERROR_ALLOWED_CODES = [400, 401, 403, 404, 429, 500, 502, 503]

CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 0
DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 30

RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
RETRY_PRIORITY_ADJUST = -1

COOKIES_ENABLED = True
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 2
COOKIES_DEBUG = False

DEFAULT_REQUEST_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-CH-UA": (
        '"Not_A Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"'
    ),
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"macOS"',
}

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
    "alkoteka_parser.middlewares.ProxyMiddleware": 350,
    "alkoteka_parser.middlewares.RegionMiddleware": 543,
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

SPIDER_MIDDLEWARES = {}

ITEM_PIPELINES = {
    'alkoteka_parser.pipelines.ValidationPipeline': 300,
    'alkoteka_parser.pipelines.DefaultValuesPipeline': 400,
    'alkoteka_parser.pipelines.DataCleaningPipeline': 500,
}

FEED_EXPORT_ENCODING = "utf-8"
FEED_FORMAT = "json"

# Кастомные экспортеры для различных форматов
FEED_EXPORTERS = {
    'json': 'scrapy.exporters.JsonItemExporter',
    'jsonl': 'alkoteka_parser.exporters.JsonLinesItemExporter',
    'csv': 'alkoteka_parser.exporters.CsvItemExporter',
    'xml': 'alkoteka_parser.exporters.XmlItemExporter',
}

HTTPCACHE_ENABLED = False
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_IGNORE_HTTP_CODES = [400, 401, 403, 404, 429, 500, 502, 503, 504]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"
HTTPCACHE_IGNORE_MISSING = True

LOG_LEVEL = "INFO"
LOG_FILE = "logs/scrapy.log"
LOG_FILE_ENCODING = "utf-8"
LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
LOG_SHORT_NAMES = False
LOGSTATS_INTERVAL = 60.0

EXTENSIONS = {
    "scrapy.extensions.logstats.LogStats": 0,
    "scrapy.extensions.spiderstate.SpiderState": 0,
    "alkoteka_parser.extensions.StatsCollector": 100,
    "alkoteka_parser.extensions.TelegramNotifier": 200,
}

# Telegram notification settings
TELEGRAM_ENABLED = False  # Set to True to enable
TELEGRAM_BOT_TOKEN = None  # Set from environment: os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = None    # Set from environment: os.getenv('TELEGRAM_CHAT_ID')

DNS_TIMEOUT = 10.0

MEMDEBUG = False
MEMDEBUG_NOTIFY = []

TARGET_DOMAIN = "alkoteka.com"
DEFAULT_REGION = "Krasnodar"
REGION_NAME = "krasnodar"

PROXY_ENABLED = False
PROXY_FILE = "proxies.txt"

TELNETCONSOLE_ENABLED = False
