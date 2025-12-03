# RegionMiddleware - Управление региональными данными

## Описание

RegionMiddleware является компонентом Scrapy, который автоматически добавляет информацию о выбранном регионе в каждый HTTP запрос. Это критически важно для сайта Алкотека, так как товары, цены и наличие зависят от текущего региона (в нашем случае - Краснодар).

## Функциональность

### 1. Установка Region Cookies
Middleware автоматически добавляет cookies, необходимые для идентификации региона:
```python
{
    'city': 'krasnodar',
    'selected_region': 'krasnodar'
}
```

Эти cookies сохраняются в сессии и отправляются со всеми последующими запросами.

### 2. Установка Region Headers
Для дополнительной идентификации региона middleware добавляет пользовательские заголовки:
```python
{
    'X-Region': 'Krasnodar',
    'X-City': 'Krasnodar'
}
```

### 3. Логирование
Все операции регионального middleware логируются на уровне DEBUG и INFO для отладки.

## Конфигурация

### settings.py
```python
REGION_NAME = "krasnodar"

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
    "alkoteka_parser.middlewares.RegionMiddleware": 543,
}
```

### Параметры
- `REGION_NAME`: Имя региона в нижнем регистре (по умолчанию "krasnodar")
- `543`: Приоритет middleware в цепи Downloader Middlewares (выполняется после UserAgent, но перед другими)

## Использование

### В паучках (spiders)
```python
class MySpider(scrapy.Spider):
    def start_requests(self):
        urls = ['https://alkoteka.com/catalog']
        for url in urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # Cookies и headers региона уже установлены middleware
        # Можно сразу парсить товары для выбранного региона
        pass
```

### Получение текущего региона
```python
from skladchik_parser.middlewares import RegionMiddleware

class MySpider(scrapy.Spider):
    def start_requests(self):
        middleware = self.crawler.engine.middleware.middlewares[RegionMiddleware]
        current_region = middleware.get_region()
        self.logger.info(f"Parsing for region: {current_region}")
```

## Механизм работы сайта Алкотека

На основе reconnaissance_report:

### Текущая конфигурация региона
- Сайт использует SPA (Single Page Application) архитектуру
- Регион упоминается в коде 89 раз
- Текущий регион определяется при первом входе
- Влияет на доступные товары, цены и акции

### Как сайт определяет регион
1. **Cookie-based**: Сайт сохраняет выбранный регион в cookies (`city`, `selected_region`)
2. **localStorage**: Вероятно, также использует browser's localStorage для сохранения выбора
3. **Session**: Информация о регионе сохраняется в сессии сервера

## Архитектура middleware

```python
class RegionMiddleware:
    def __init__(self, crawler):
        # Инициализация с чтением REGION_NAME из settings
        self.region = crawler.settings.get('REGION_NAME', 'krasnodar')

    def process_request(self, request, spider):
        # Применяется к каждому запросу перед его отправкой
        self._set_region_cookie(request)    # Добавляет cookies
        self._set_region_headers(request)   # Добавляет headers
        return None  # Продолжить обработку запроса

    def _set_region_cookie(self, request):
        # Добавляет cookies только если их нет
        # Не переопределяет существующие cookies

    def _set_region_headers(self, request):
        # Добавляет заголовки только если их нет
        # Не переопределяет существующие заголовки

    def get_region(self):
        # Метод для получения текущего региона из других компонентов
```

## Порядок выполнения Downloader Middlewares

1. **400 - RandomUserAgentMiddleware** - Установка случайного User-Agent
2. **543 - RegionMiddleware** (ЭТО МЕСТО) - Установка региональных данных
3. Другие middlewares...

## Поддерживаемые регионы

На основе reconnaissance_report, поддерживаются:
- Все крупные города России (вероятно)
- Главный город: Краснодар (текущая конфигурация)

Для изменения региона в сессии парсинга:

```python
# В command-line
scrapy crawl my_spider -a REGION_NAME=moscow

# В settings.py
REGION_NAME = "moscow"  # Изменить на нужный город
```

## Особенности реализации

### Безопасность cookie установки
```python
if key not in request.cookies:
    request.cookies[key] = value
```
Проверяет, не переопределяет ли уже установленные cookies. Это важно, если:
- Spider уже установил эти cookies
- Сервер отправил Set-Cookie заголовок

### Капитализация headers
```python
'X-Region': self.region.capitalize()  # 'krasnodar' -> 'Krasnodar'
```
Headers требуют правильного форматирования для совместимости с браузерами.

## Логирование

Middleware логирует:
- Инициализацию: `RegionMiddleware initialized with region: krasnodar`
- Обработку каждого запроса на уровне DEBUG
- Любые ошибки на уровне ERROR

Включить DEBUG логирование:
```python
LOG_LEVEL = "DEBUG"  # В settings.py
```

## Возможные расширения

### 1. Динамическое изменение региона
```python
def process_request(self, request, spider):
    if hasattr(spider, 'target_region'):
        self.region = spider.target_region
```

### 2. Валидация региона
```python
VALID_REGIONS = ['krasnodar', 'moscow', 'spb', 'novosibirsk']

def _validate_region(self):
    if self.region not in VALID_REGIONS:
        raise ValueError(f"Invalid region: {self.region}")
```

### 3. Автоматическое определение региона
```python
def _auto_detect_region(self, response):
    # Парсить выбранный регион из ответа сервера
    # и обновить self.region
```

## Тестирование

```python
from scrapy.http import Request
from alkoteka_parser.middlewares import RegionMiddleware

def test_region_middleware():
    request = Request('https://alkoteka.com/catalog')
    middleware = RegionMiddleware(crawler)

    middleware.process_request(request, spider)

    assert 'city' in request.cookies
    assert request.cookies['city'] == 'krasnodar'
    assert 'X-Region' in request.headers
```

## Проблемы и решения

### Проблема: Cookies не сохраняются
**Решение:** Убедиться, что `COOKIES_ENABLED = True` в settings.py

### Проблема: Регион не применяется ко всем запросам
**Решение:** Проверить приоритет middleware (должно быть > 400)

### Проблема: Сайт требует инициализацию региона через API
**Решение:** Создать специальный паук для инициализации региона перед основным парсингом

## Дополнительные ссылки

- [Scrapy Downloader Middlewares](https://docs.scrapy.org/en/latest/topics/downloader-middleware.html)
- [Scrapy Request/Response](https://docs.scrapy.org/en/latest/topics/request-response.html)
- [reconnaissance_report.md](./reconnaissance_report.md) - Анализ сайта Алкотека
