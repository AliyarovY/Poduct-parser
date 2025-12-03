# Пример конфигурации Scrapy

Этот файл содержит примеры конфигурирования проекта для различных сценариев.

## 1. Стандартная конфигурация (settings.py)

```python
# Основные настройки
BOT_NAME = "alkoteka_parser"
SPIDER_MODULES = ["alkoteka_parser.spiders"]
NEWSPIDER_MODULE = "alkoteka_parser.spiders"

# User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# robots.txt
ROBOTSTXT_OBEY = False
HTTPERROR_ALLOWED_CODES = [400, 401, 403, 404, 429, 500, 502, 503]

# Скорость и нагрузка
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 30

# Retry механизм
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
RETRY_PRIORITY_ADJUST = -1

# Cookies и Redirect
COOKIES_ENABLED = True
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 2

# Default Headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}

# Middleware
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
    "alkoteka_parser.middlewares.ProxyMiddleware": 350,
    "alkoteka_parser.middlewares.RegionMiddleware": 543,
}

# AutoThrottle
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Pipelines
ITEM_PIPELINES = {
    'alkoteka_parser.pipelines.ValidationPipeline': 300,
    'alkoteka_parser.pipelines.DefaultValuesPipeline': 400,
    'alkoteka_parser.pipelines.DataCleaningPipeline': 500,
}

# Логирование
LOG_LEVEL = "INFO"
LOG_FILE = "logs/scrapy.log"
LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"

# Regional Settings
TARGET_DOMAIN = "alkoteka.com"
DEFAULT_REGION = "Krasnodar"
REGION_NAME = "krasnodar"

# Proxy Settings
PROXY_ENABLED = False
PROXY_FILE = "proxies.txt"
```

## 2. Конфигурация для высокой скорости (агрессивная)

```python
# Для быстрого сбора данных (с риском блокировки)
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0.5
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = False  # Отключаем auto-throttle для максимальной скорости
RETRY_TIMES = 1  # Минимум повторов
PROXY_ENABLED = True  # Используем прокси для избежания блокировки
```

## 3. Конфигурация для тестирования (медленная, безопасная)

```python
# Для отладки и тестирования
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 5
RANDOMIZE_DOWNLOAD_DELAY = True
LOG_LEVEL = "DEBUG"
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_MAX_DELAY = 30
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
COOKIES_ENABLED = True
PROXY_ENABLED = False
```

## 4. Конфигурация по регионам

### Краснодар (по умолчанию)
```python
DEFAULT_REGION = "Krasnodar"
REGION_NAME = "krasnodar"
```

### Москва
```python
DEFAULT_REGION = "Moscow"
REGION_NAME = "moscow"
```

### Санкт-Петербург
```python
DEFAULT_REGION = "Saint Petersburg"
REGION_NAME = "saint-petersburg"
```

## 5. Конфигурация Proxy

### Использование прокси из файла

Создайте файл `proxies.txt` в корне проекта:

```
http://proxy1.example.com:8080
http://proxy2.example.com:8080
socks5://proxy3.example.com:1080
http://user:password@proxy4.example.com:8080
```

Затем в settings.py:
```python
PROXY_ENABLED = True
PROXY_FILE = "proxies.txt"
```

### Отключение прокси
```python
PROXY_ENABLED = False
```

## 6. Конфигурация логирования

### Подробное логирование (DEBUG)
```python
LOG_LEVEL = "DEBUG"
LOG_FILE = "logs/scrapy_debug.log"
LOGSTATS_INTERVAL = 30  # Статистика каждые 30 сек
```

### Минимальное логирование (WARNING)
```python
LOG_LEVEL = "WARNING"
LOG_FILE = "logs/scrapy_production.log"
LOGSTATS_INTERVAL = 300  # Статистика каждые 5 минут
```

### Логирование в консоль
```python
LOG_LEVEL = "INFO"
# Не указываем LOG_FILE, логи идут в stdout
```

## 7. Примеры запуска с разными конфигурациями

### Стандартный запуск
```bash
cd alkoteka_parser
scrapy crawl alkoteka -O result.json
```

### Запуск с DEBUG логированием
```bash
scrapy crawl alkoteka -O result.json -L DEBUG
```

### Запуск только одной категории (редактируя spider)

В файле `spiders/alkoteka_spider.py` измените START_URLS:

```python
START_URLS = [
    'https://alkoteka.com/catalog/category/vodka/',
]
```

Затем:
```bash
scrapy crawl alkoteka -O vodka_only.json
```

### Запуск с кастомными аргументами

```bash
scrapy crawl alkoteka -a region=Moscow -O moscow.json
```

## 8. Оптимальные настройки для разных сценариев

### Сценарий 1: Полный парсинг всех категорий
```python
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 2
AUTOTHROTTLE_ENABLED = True
PROXY_ENABLED = True
RETRY_TIMES = 3
```

### Сценарий 2: Быстрая проверка (мало товаров)
```python
CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 0.5
AUTOTHROTTLE_ENABLED = False
PROXY_ENABLED = False
RETRY_TIMES = 1
```

### Сценарий 3: Долгоживущий процесс (23+ часа)
```python
CONCURRENT_REQUESTS = 2
DOWNLOAD_DELAY = 3
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_MAX_DELAY = 30
PROXY_ENABLED = True
COOKIES_ENABLED = True
RETRY_TIMES = 5
```

## 9. Проверка конфигурации

Для проверки текущей конфигурации:

```bash
cd alkoteka_parser
scrapy settings --get CONCURRENT_REQUESTS
scrapy settings --get DOWNLOAD_DELAY
scrapy settings --get LOG_LEVEL
```

Для просмотра всех текущих настроек:

```bash
scrapy settings
```

## 10. Полезные ссылки

- [Документация Scrapy Settings](https://docs.scrapy.org/en/latest/topics/settings.html)
- [Middleware документация](https://docs.scrapy.org/en/latest/topics/downloader-middleware.html)
- [Pipeline документация](https://docs.scrapy.org/en/latest/topics/item-pipeline.html)
