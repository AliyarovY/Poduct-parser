import scrapy
import json
import os
import time
import re
from typing import Generator, Optional, Dict, Any
from twisted.internet.error import DNSLookupError, TimeoutError, ConnectionRefusedError
from ..item_loaders import ProductItemLoader
from ..items import ProductItem


class AlkotekaSpider(scrapy.Spider):
    """
    Scrapy spider for parsing products from Alkoteka.com (Russian alcohol e-commerce site).

    This spider handles:
    - Parsing product categories
    - Extracting product details (name, price, images, ratings, etc.)
    - Detecting product variants (volume, color, etc.)
    - Handling errors and retries gracefully
    - Managing regional settings through middleware

    Attributes:
        name (str): Spider identifier 'alkoteka'
        allowed_domains (list): List of allowed domains
        custom_settings (dict): Custom Scrapy settings for this spider
        START_URLS (list): List of category URLs to start parsing from
    """

    name = 'alkoteka'
    allowed_domains = ['alkoteka.com']

    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'DOWNLOAD_DELAY': 2,
    }

    START_URLS = [
        'https://alkoteka.com/catalog/category/vodka/',
        'https://alkoteka.com/catalog/category/konyak/',
        'https://alkoteka.com/catalog/category/pivo/',
        'https://alkoteka.com/catalog/category/vino/',
        'https://alkoteka.com/catalog/category/viski/',
    ]

    def __init__(self, *args, **kwargs):
        """
        Initialize the spider with category data and stats tracking.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.categories = self._load_categories()
        self.stats_data = {
            'categories_parsed': 0,
            'products_found': 0,
            'pages_parsed': 0,
        }

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """
        Generate initial requests for all product categories.

        Yields:
            scrapy.Request: Request objects for each category page

        @contract
        @returns requests 1 100
        """
        if self.categories:
            for category in self.categories:
                yield scrapy.Request(
                    url=category['url'],
                    callback=self.parse_category,
                    errback=self.errback_handler,
                    meta={
                        'category_id': category['id'],
                        'category_name': category['name'],
                        'page': 1,
                    }
                )
        else:
            for url in self.START_URLS:
                category_name = url.split('/')[-2].capitalize()
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_category,
                    errback=self.errback_handler,
                    meta={
                        'category_name': category_name,
                        'page': 1,
                    }
                )

    def parse_category(self, response):
        """
        Parse a category page and extract product links.

        Handles:
        - Extracting product links from various selectors
        - Yielding requests for each product
        - Handling pagination to next pages
        - Tracking statistics

        Args:
            response (scrapy.http.Response): Category page response

        Yields:
            scrapy.Request: Requests for product pages and next category pages

        @contract
        @url https://alkoteka.com/catalog/category/vodka/
        @returns requests 1 100
        """
        try:
            category_name = response.meta.get('category_name', 'Unknown')
            category_id = response.meta.get('category_id', 'N/A')
            page = response.meta.get('page', 1)

            product_links = response.css('a.product-link::attr(href)').getall()

            if not product_links:
                product_links = response.css('a.catalog-product::attr(href)').getall()

            if not product_links:
                product_links = self._extract_product_links_from_html(response)

            if product_links:
                self.logger.info(f"Category: {category_name} (ID: {category_id}), Page: {page}, Found: {len(product_links)} products")
                self.stats_data['products_found'] += len(product_links)

                for product_url in product_links:
                    absolute_url = response.urljoin(product_url)
                    yield scrapy.Request(
                        url=absolute_url,
                        callback=self.parse_product,
                        errback=self.errback_handler,
                        meta={
                            'category_id': category_id,
                            'category_name': category_name,
                        }
                    )
            else:
                self.logger.warning(f"No products found in category: {category_name}, page: {page}")

            next_page = self._get_next_page_url(response)
            if next_page:
                self.logger.debug(f"Found next page for {category_name}: {next_page}")
                yield scrapy.Request(
                    url=response.urljoin(next_page),
                    callback=self.parse_category,
                    errback=self.errback_handler,
                    meta={
                        'category_id': category_id,
                        'category_name': category_name,
                        'page': page + 1,
                    }
                )
            else:
                self.stats_data['categories_parsed'] += 1

            self.stats_data['pages_parsed'] += 1

        except Exception as e:
            self.logger.error(f"Error parsing category {response.meta.get('category_name')} at {response.url}: {str(e)}")

    def parse_product(self, response):
        """
        Parse a product page and extract all product details.

        Extracts:
        - Basic info (ID, name, URL, category)
        - Price information (current, original, discount)
        - Images and descriptions
        - Ratings and reviews
        - Stock information
        - Product variants (volume, color, etc.)
        - Marketing tags

        Args:
            response (scrapy.http.Response): Product page response

        Yields:
            ProductItem: Processed product item with all extracted data

        @contract
        @url https://alkoteka.com/product/test-product/
        @returns items 0 1
        """
        try:
            if not response.css('h1, .product-title, .title'):
                self.logger.warning(f"Product page not found or empty at {response.url}")
                return

            loader = ProductItemLoader(item=ProductItem(), response=response)

            loader.add_value('product_id', self._extract_product_id(response))
            loader.add_value('scraped_at', int(time.time()))
            loader.add_value('product_url', response.url)

            title = self._extract_title(response)
            if title:
                loader.add_value('name', title)

            brand = self._extract_brand(response)
            if brand:
                loader.add_value('brand', brand)

            sku = self._extract_sku(response)
            if sku:
                loader.add_value('sku', sku)

            breadcrumbs = self._extract_breadcrumbs(response)
            if breadcrumbs:
                loader.add_value('category', breadcrumbs[-1] if breadcrumbs else None)

            tags = self._extract_marketing_tags(response)
            if tags:
                loader.add_value('attributes', {'marketing_tags': tags})

            price_data = self._extract_price_data(response)
            if price_data:
                loader.add_value('price_data', price_data)
                if price_data.get('current'):
                    loader.add_value('price', price_data['current'])
                if price_data.get('original'):
                    loader.add_value('original_price', price_data['original'])

            stock_data = self._extract_stock_data(response)
            if stock_data:
                loader.add_value('stock_data', stock_data)
                if stock_data.get('in_stock') is not None:
                    loader.add_value('in_stock', stock_data['in_stock'])
                if stock_data.get('count') is not None:
                    loader.add_value('stock_quantity', stock_data['count'])
                if stock_data.get('status'):
                    loader.add_value('availability_status', stock_data['status'])

            assets = self._extract_assets(response)
            if assets:
                loader.add_value('assets', assets)
                if assets.get('main_image'):
                    loader.add_value('image_url', assets['main_image'])
                if assets.get('gallery_images'):
                    loader.add_value('image_urls', assets['gallery_images'])

            description = self._extract_description(response)
            if description:
                loader.add_value('description', description)

            characteristics = self._extract_characteristics(response)
            if characteristics:
                for key, value in characteristics.items():
                    if key.lower() in ('объем', 'volume', 'size'):
                        loader.add_value('volume', value)
                    elif key.lower() in ('крепость', 'alcohol content', 'abv'):
                        loader.add_value('alcohol_content', value)
                    elif key.lower() in ('страна', 'country', 'производство'):
                        loader.add_value('country', value)
                    elif key.lower() in ('год', 'year', 'vintage'):
                        loader.add_value('year', value)

            metadata = self._extract_metadata(response)
            if metadata:
                loader.add_value('attributes', metadata)

            loader.add_css('rating', 'span.rating-value::text')
            loader.add_css('review_count', 'span.review-count::text')

            variants_count = self._detect_variants(response)
            if variants_count > 0:
                loader.add_value('attributes', {'variants_count': variants_count})
                if variants_count > 1:
                    self.logger.info(f"Product {response.url} has {variants_count} variants")

            loader.add_value('category', response.meta.get('category_name'))
            loader.add_value('category_id', response.meta.get('category_id'))
            loader.add_value('region', self.settings.get('REGION_NAME', 'krasnodar'))
            loader.add_value('source', 'alkoteka.com')

            item = loader.load_item()

            if item.get('name'):
                yield item
            else:
                self.logger.warning(f"Failed to parse product at {response.url}")

        except Exception as e:
            self.logger.error(f"Error parsing product at {response.url}: {str(e)}")
            self.logger.debug(f"Exception type: {type(e).__name__}")

    def _load_categories(self) -> list:
        """
        Load product categories from categories.json file.

        Returns:
            list: List of category dictionaries with 'id', 'name', and 'url' keys
        """
        try:
            categories_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'categories.json'
            )
            if os.path.exists(categories_file):
                with open(categories_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading categories.json: {e}")
        return []

    def _extract_product_links_from_html(self, response) -> list:
        links = []

        product_cards = response.css('div.product-card, div.product-item, div[class*="product"]')
        for card in product_cards:
            link = card.css('a::attr(href)').get()
            if link:
                links.append(link)

        return links

    def _get_next_page_url(self, response) -> Optional[str]:
        next_button = response.css('a.next-page::attr(href)').get()
        if next_button:
            return next_button

        next_button = response.css('a[rel="next"]::attr(href)').get()
        if next_button:
            return next_button

        next_button = response.css('a:contains("Следующая")::attr(href)').get()
        if next_button:
            return next_button

        last_page_link = response.css('a.pagination-link:last-child::attr(href)').get()
        if last_page_link and 'page' in response.url and last_page_link not in response.url:
            return last_page_link

        return None

    def _extract_product_id(self, response) -> str:
        product_id = response.css('div[data-product-id]::attr(data-product-id)').get()
        if product_id:
            return product_id

        product_id = response.css('input[name="product_id"]::attr(value)').get()
        if product_id:
            return product_id

        url_parts = response.url.split('/')
        for part in reversed(url_parts):
            if part.isdigit():
                return part

        return response.url.split('/')[-1]

    def _extract_title(self, response) -> Optional[str]:
        title = response.css('h1.product-title::text').get()
        if not title:
            title = response.css('h1::text').get()
        if not title:
            title = response.css('.product-name::text').get()

        if title:
            title = title.strip()
            volume = self._extract_volume(response)
            if volume and volume not in title:
                title = f"{title} {volume}"
            return title
        return None

    def _extract_volume(self, response) -> Optional[str]:
        volume = response.css('[data-volume]::attr(data-volume)').get()
        if volume:
            return volume.strip()

        volume = response.css('.product-volume::text').get()
        if volume:
            return volume.strip()

        volume_match = response.xpath('//span[contains(text(), "мл") or contains(text(), "л")]//text()').get()
        if volume_match:
            return volume_match.strip()

        return None

    def _extract_brand(self, response) -> Optional[str]:
        brand = response.css('.brand-name::text').get()
        if not brand:
            brand = response.css('[data-brand]::attr(data-brand)').get()
        if not brand:
            brand = response.css('a.brand-link::text').get()

        return brand.strip() if brand else None

    def _extract_sku(self, response) -> Optional[str]:
        sku = response.css('[data-sku]::attr(data-sku)').get()
        if sku:
            return sku.strip()

        sku = response.css('input[name="sku"]::attr(value)').get()
        if sku:
            return sku.strip()

        sku_text = response.xpath('//label[contains(text(), "SKU") or contains(text(), "Артикул")]/../text()').get()
        if sku_text:
            return sku_text.strip()

        return None

    def _extract_breadcrumbs(self, response) -> list:
        breadcrumbs = response.css('.breadcrumb a::text').getall()
        if not breadcrumbs:
            breadcrumbs = response.css('.breadcrumb-link::text').getall()
        if not breadcrumbs:
            breadcrumbs = response.xpath('//nav[@class="breadcrumb"]//a/text()').getall()

        return [b.strip() for b in breadcrumbs if b.strip()] if breadcrumbs else []

    def _extract_marketing_tags(self, response) -> list:
        tags = response.css('.product-tag::text').getall()
        if not tags:
            tags = response.css('.tag::text').getall()
        if not tags:
            tags = response.css('[class*="badge"]::text').getall()

        return [t.strip() for t in tags if t.strip() and len(t.strip()) > 1] if tags else []

    def _extract_price_data(self, response) -> Optional[Dict[str, Any]]:
        current_price = self._extract_current_price(response)
        original_price = self._extract_original_price(response)

        if not current_price:
            return None

        if not original_price:
            original_price = current_price

        sale_tag = None
        discount = self._calculate_discount(original_price, current_price)
        if discount and discount > 0:
            sale_tag = f"Скидка {discount}%"

        return {
            'current': current_price,
            'original': original_price,
            'sale_tag': sale_tag,
            'currency': 'RUB'
        }

    def _extract_current_price(self, response) -> Optional[float]:
        price = response.css('.price-current::text').get()
        if not price:
            price = response.css('.product-price::text').get()
        if not price:
            price = response.css('[data-price]::attr(data-price)').get()
        if not price:
            price = response.xpath('//span[contains(@class, "price")]//text()').get()

        return self._clean_price(price) if price else None

    def _extract_original_price(self, response) -> Optional[float]:
        price = response.css('.price-old::text').get()
        if not price:
            price = response.css('.price-original::text').get()
        if not price:
            price = response.css('[data-original-price]::attr(data-original-price)').get()
        if not price:
            price = response.css('.product-original-price::text').get()

        return self._clean_price(price) if price else None

    def _clean_price(self, price_string: str) -> Optional[float]:
        if not price_string:
            return None

        cleaned = price_string.strip()
        cleaned = re.sub(r'[^\d.,]', '', cleaned)
        cleaned = cleaned.replace(',', '.')
        cleaned = cleaned.replace(' ', '')

        try:
            return float(cleaned)
        except (ValueError, AttributeError):
            return None

    def _calculate_discount(self, original: float, current: float) -> Optional[int]:
        if not original or not current or original <= 0:
            return None
        discount = ((original - current) / original) * 100
        return int(max(0, min(100, discount)))

    def _extract_stock_data(self, response) -> Optional[Dict[str, Any]]:
        in_stock = self._check_in_stock(response)
        count = self._extract_stock_count(response)
        status = self._extract_stock_status(response)

        if in_stock is None and not status:
            return None

        return {
            'in_stock': in_stock if in_stock is not None else True,
            'count': count if count is not None else 0,
            'status': status,
            'available_regions': []
        }

    def _check_in_stock(self, response) -> Optional[bool]:
        buy_button = response.css('button.buy-btn, button[data-action="add-to-cart"]').get()
        if buy_button:
            return True

        in_stock_text = response.css('.in-stock, .availability-in-stock::text').get()
        if in_stock_text and 'в наличии' in in_stock_text.lower():
            return True

        out_of_stock = response.css('.out-of-stock, .availability-out::text').get()
        if out_of_stock and 'нет' in out_of_stock.lower():
            return False

        preorder = response.css('.preorder, [data-preorder]::text').get()
        if preorder:
            return None

        return None

    def _extract_stock_count(self, response) -> Optional[int]:
        text = response.xpath('//text()').get()
        if text:
            match = re.search(r'(\d+)\s*шт', text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass

        count_text = response.css('[data-stock-count]::attr(data-stock-count)').get()
        if count_text:
            try:
                return int(count_text)
            except ValueError:
                pass

        return None

    def _extract_stock_status(self, response) -> Optional[str]:
        status_text = response.css('.stock-status::text, .availability-text::text').get()
        if status_text:
            return status_text.strip()

        if response.css('.preorder, [data-preorder]').get():
            return 'Предзаказ'

        if response.css('.on-order').get():
            return 'Под заказ'

        if response.css('.out-of-stock').get():
            return 'Нет в наличии'

        if response.css('.in-stock').get():
            return 'В наличии'

        return None

    def _extract_assets(self, response) -> Optional[Dict[str, Any]]:
        main_image = self._extract_main_image(response)
        gallery_images = self._extract_gallery_images(response)
        view_360 = self._extract_360_view(response)
        video_urls = self._extract_video_urls(response)

        if not main_image and not gallery_images and not video_urls:
            return None

        return {
            'main_image': main_image,
            'gallery_images': gallery_images if gallery_images else [],
            'view_360': view_360 if view_360 else [],
            'video': video_urls if video_urls else [],
            'cached_images': []
        }

    def _extract_main_image(self, response) -> Optional[str]:
        main_img = response.css('.product-image-main img::attr(src)').get()
        if not main_img:
            main_img = response.css('.product-main-image::attr(src)').get()
        if not main_img:
            main_img = response.css('img[class*="main"]::attr(src)').get()
        if not main_img:
            main_img = response.css('[data-main-image]::attr(data-main-image)').get()

        if main_img:
            return self._normalize_url(response, main_img)
        return None

    def _extract_gallery_images(self, response) -> list:
        images = response.css('.product-gallery img::attr(src)').getall()
        if not images:
            images = response.css('.product-carousel img::attr(src)').getall()
        if not images:
            images = response.css('[class*="gallery"] img::attr(src)').getall()
        if not images:
            images = response.xpath('//img[contains(@class, "product")]/@src').getall()

        if not images:
            images = self._extract_images_from_json(response)

        normalized = []
        seen = set()
        for img in images:
            if img:
                normalized_url = self._normalize_url(response, img)
                if normalized_url and normalized_url not in seen:
                    normalized.append(normalized_url)
                    seen.add(normalized_url)

        return sorted(normalized)

    def _extract_images_from_json(self, response) -> list:
        images = []
        try:
            json_scripts = response.xpath('//script[@type="application/json"]/text()').getall()
            for script_content in json_scripts:
                if 'image' in script_content.lower() or 'src' in script_content.lower():
                    try:
                        data = json.loads(script_content)
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if 'image' in key.lower() and isinstance(value, str):
                                    images.append(value)
                                elif 'src' in key.lower() and isinstance(value, str):
                                    images.append(value)
                                elif isinstance(value, list):
                                    for item in value:
                                        if isinstance(item, dict):
                                            for k, v in item.items():
                                                if 'image' in k.lower() or 'src' in k.lower():
                                                    if isinstance(v, str):
                                                        images.append(v)
                    except (json.JSONDecodeError, ValueError):
                        pass
        except Exception:
            pass
        return images

    def _extract_360_view(self, response) -> list:
        view_360 = response.css('[data-360]::attr(data-360)').getall()
        if not view_360:
            view_360 = response.css('.view-360 img::attr(src)').getall()
        if not view_360:
            view_360 = response.xpath('//img[contains(@data-type, "360")]/@src').getall()

        normalized = []
        seen = set()
        for img in view_360:
            if img:
                normalized_url = self._normalize_url(response, img)
                if normalized_url and normalized_url not in seen:
                    normalized.append(normalized_url)
                    seen.add(normalized_url)

        return sorted(normalized) if normalized else []

    def _extract_video_urls(self, response) -> list:
        video_urls = []

        video_sources = response.css('video source::attr(src)').getall()
        for src in video_sources:
            if src:
                normalized = self._normalize_url(response, src)
                if normalized and normalized not in video_urls:
                    video_urls.append(normalized)

        youtube_iframes = response.css('iframe[src*="youtube"]::attr(src)').getall()
        for iframe_src in youtube_iframes:
            if iframe_src:
                if not iframe_src.startswith('http'):
                    iframe_src = response.urljoin(iframe_src)
                if iframe_src not in video_urls:
                    video_urls.append(iframe_src)

        vimeo_iframes = response.css('iframe[src*="vimeo"]::attr(src)').getall()
        for iframe_src in vimeo_iframes:
            if iframe_src:
                if not iframe_src.startswith('http'):
                    iframe_src = response.urljoin(iframe_src)
                if iframe_src not in video_urls:
                    video_urls.append(iframe_src)

        video_tags = response.css('video::attr(src)').getall()
        for video_src in video_tags:
            if video_src:
                normalized = self._normalize_url(response, video_src)
                if normalized and normalized not in video_urls:
                    video_urls.append(normalized)

        return video_urls

    def _normalize_url(self, response, url: str) -> Optional[str]:
        if not url:
            return None

        url = url.strip()

        if url.startswith('http://') or url.startswith('https://'):
            return url

        if url.startswith('//'):
            return f"https:{url}"

        return response.urljoin(url)

    def _extract_description(self, response) -> Optional[str]:
        description = response.css('.product-description::text').get()
        if not description:
            description = response.css('[class*="description"]::text').get()
        if not description:
            description = response.xpath('//div[contains(@class, "description")]//text()').get()
        if not description:
            description = response.css('p.product-text::text').get()

        return description.strip() if description else None

    def _extract_characteristics(self, response) -> Dict[str, str]:
        characteristics = {}

        characteristics.update(self._parse_table_characteristics(response))

        if not characteristics:
            characteristics.update(self._parse_list_characteristics(response))

        if not characteristics:
            characteristics.update(self._parse_div_characteristics(response))

        characteristics.update(self._extract_jsonld_characteristics(response))

        return characteristics

    def _parse_table_characteristics(self, response) -> Dict[str, str]:
        chars = {}
        try:
            for row in response.css('table.characteristics tr, table.specs tr, table[class*="char"] tr'):
                key = row.css('.char-name::text, .spec-name::text, td:first-child::text').get()
                value = row.css('.char-value::text, .spec-value::text, td:last-child::text').get()

                if not key:
                    cells = row.css('td::text').getall()
                    if len(cells) >= 2:
                        key = cells[0]
                        value = cells[-1]

                if key and value:
                    key_cleaned = key.strip()
                    value_cleaned = value.strip()
                    if key_cleaned and value_cleaned:
                        chars[key_cleaned] = value_cleaned
        except Exception:
            pass

        return chars

    def _parse_list_characteristics(self, response) -> Dict[str, str]:
        chars = {}
        try:
            for item in response.css('.specs-list, .characteristics-list, [class*="specs"]'):
                key = item.css('dt::text, .spec-label::text, .label::text').get()
                value = item.css('dd::text, .spec-value::text, .value::text').get()

                if key and value:
                    key_cleaned = key.strip()
                    value_cleaned = value.strip()
                    if key_cleaned and value_cleaned:
                        chars[key_cleaned] = value_cleaned
        except Exception:
            pass

        return chars

    def _parse_div_characteristics(self, response) -> Dict[str, str]:
        chars = {}
        try:
            for spec_div in response.css('[class*="specification"], [class*="feature"], [class*="attribute"]'):
                key_elem = spec_div.css('[class*="key"], [class*="name"], [class*="label"]::text').get()
                value_elem = spec_div.css('[class*="value"], [class*="content"]::text').get()

                if key_elem and value_elem:
                    key_cleaned = key_elem.strip()
                    value_cleaned = value_elem.strip()
                    if key_cleaned and value_cleaned:
                        chars[key_cleaned] = value_cleaned
        except Exception:
            pass

        return chars

    def _extract_jsonld_characteristics(self, response) -> Dict[str, str]:
        chars = {}
        try:
            jsonld_scripts = response.css('script[type="application/ld+json"]::text').getall()
            for script_content in jsonld_scripts:
                try:
                    data = json.loads(script_content)
                    if isinstance(data, dict):
                        if 'additionalProperty' in data:
                            props = data.get('additionalProperty', [])
                            for prop in props:
                                if isinstance(prop, dict):
                                    name = prop.get('name', '')
                                    value = prop.get('value', '')
                                    if name and value:
                                        chars[str(name)] = str(value)

                        for key, value in data.items():
                            if key not in ('@context', '@type', 'url', 'image', 'name', 'description'):
                                if isinstance(value, str) and len(value) < 200:
                                    chars[key] = value
                except (json.JSONDecodeError, ValueError):
                    pass
        except Exception:
            pass

        return chars

    def _extract_metadata(self, response) -> Dict[str, Any]:
        metadata = {}

        metadata['__description'] = self._extract_description(response) or ''

        metadata['volume'] = self._extract_special_field(response, 'volume', ['объем', 'volume', 'size'])
        metadata['alcohol_content'] = self._extract_special_field(response, 'alcohol', ['крепость', 'alcohol', 'abv'])
        metadata['country'] = self._extract_special_field(response, 'country', ['страна', 'country', 'производство'])
        metadata['year'] = self._extract_special_field(response, 'year', ['год', 'year', 'vintage'])

        metadata['sku'] = self._extract_special_field(response, 'sku', ['артикул', 'sku', 'product code'])
        metadata['product_code'] = self._extract_special_field(response, 'code', ['код', 'code', 'product code'])

        metadata['characteristics'] = self._extract_characteristics(response)

        return metadata

    def _extract_special_field(self, response, field_name: str, keywords: list) -> Optional[str]:
        chars = self._extract_characteristics(response)
        for key, value in chars.items():
            if any(kw in key.lower() for kw in keywords):
                return value

        css_selector = f'[data-{field_name}]::attr(data-{field_name})'
        value = response.css(css_selector).get()
        if value:
            return value.strip()

        return None

    def _detect_variants(self, response) -> int:
        """
        Detect and count product variants (volume, color, etc.).

        Combines variants from multiple sources:
        1. Volume selectors (dropdown options)
        2. Color variants (buttons, links)
        3. JSON structures in data attributes

        Args:
            response (scrapy.http.Response): Product page response

        Returns:
            int: Count of detected and validated variants
        """
        variants = set()

        volume_variants = self._extract_volume_variants(response)
        variants.update(volume_variants)

        color_variants = self._extract_color_variants(response)
        variants.update(color_variants)

        json_variants_count = self._extract_variants_from_json(response)
        if json_variants_count > 0:
            return json_variants_count

        valid_variants = [v for v in variants if self._validate_variant(v)]
        return len(valid_variants)

    def _extract_volume_variants(self, response) -> list:
        variants = []

        option_variants = response.css('.volume-selector option::text').getall()
        if not option_variants:
            option_variants = response.css('select[name*="volume"] option::text').getall()
        if not option_variants:
            option_variants = response.css('select[class*="volume"] option::text').getall()

        for opt in option_variants:
            if opt and opt.strip():
                cleaned = opt.strip()
                if self._validate_variant(cleaned):
                    variants.append(cleaned)

        button_variants = response.css('.volume-btn::text').getall()
        if not button_variants:
            button_variants = response.css('[class*="volume"][class*="btn"]::text').getall()
        if not button_variants:
            button_variants = response.css('.size-button[data-volume]::text').getall()

        for btn in button_variants:
            if btn and btn.strip():
                cleaned = btn.strip()
                if self._validate_variant(cleaned):
                    variants.append(cleaned)

        return self._deduplicate_variants(variants)

    def _extract_color_variants(self, response) -> list:
        variants = []

        color_options = response.css('.color-selector option::text').getall()
        if not color_options:
            color_options = response.css('select[name*="color"] option::text').getall()
        if not color_options:
            color_options = response.css('select[class*="color"] option::text').getall()

        for opt in color_options:
            if opt and opt.strip():
                cleaned = opt.strip()
                if 'color' in response.url.lower() or 'цвет' in cleaned.lower():
                    if self._validate_variant(cleaned):
                        variants.append(cleaned)

        color_buttons = response.css('.color-btn::text').getall()
        if not color_buttons:
            color_buttons = response.css('[class*="color"][class*="btn"]::text').getall()
        if not color_buttons:
            color_buttons = response.css('[data-color]::text').getall()

        for btn in color_buttons:
            if btn and btn.strip():
                cleaned = btn.strip()
                if self._validate_variant(cleaned):
                    variants.append(cleaned)

        color_from_attrs = response.css('[data-available-colors]::attr(data-available-colors)').get()
        if color_from_attrs:
            try:
                colors = json.loads(color_from_attrs)
                if isinstance(colors, list):
                    for color in colors:
                        if isinstance(color, str) and self._validate_variant(color):
                            variants.append(color)
            except (json.JSONDecodeError, ValueError):
                pass

        return self._deduplicate_variants(variants)

    def _extract_variants_from_json(self, response) -> int:
        try:
            variants_json = response.css('[data-variants]::attr(data-variants)').get()
            if not variants_json:
                variants_json = response.xpath('//script[@type="application/json"][contains(., "variants")]/text()').get()

            if variants_json:
                data = json.loads(variants_json)
                if isinstance(data, dict):
                    if 'variants' in data and isinstance(data['variants'], list):
                        return len([v for v in data['variants'] if self._validate_variant(str(v))])
                    if 'options' in data and isinstance(data['options'], list):
                        return len([o for o in data['options'] if self._validate_variant(str(o))])
                elif isinstance(data, list):
                    return len([v for v in data if self._validate_variant(str(v))])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        return 0

    def _deduplicate_variants(self, variants: list) -> list:
        seen = {}
        unique = []
        for variant in variants:
            normalized = variant.lower().strip()
            if normalized not in seen:
                seen[normalized] = True
                unique.append(variant)
        return unique

    def _validate_variant(self, variant: str) -> bool:
        if not variant or not isinstance(variant, str):
            return False

        normalized = variant.lower().strip()

        if not normalized or len(normalized) > 100:
            return False

        invalid_keywords = [
            'размер', 'size', 'одежда', 'clothing', 'shirt', 'pants', 'dress',
            'обувь', 'shoe', 'носок', 'sock',
            'width', 'длина', 'height', 'высота',
            'material', 'материал', 'ткань', 'fabric',
            'large', 'small', 'medium', 'extra'
        ]

        size_patterns = [
            r'^\s*(xs|s|m|l|xl|xxl)\s*$',
            r'size\s+(xs|s|m|l|xl|xxl)',
            r'(xs|s|m|l|xl|xxl)\s*size'
        ]

        for keyword in invalid_keywords:
            if keyword in normalized:
                return False

        import re
        for pattern in size_patterns:
            if re.match(pattern, normalized):
                return False

        if normalized in ('select', 'выбрать', 'choose', 'выбор'):
            return False

        return True

    def errback_handler(self, failure):
        """
        Handle errors that occur during request processing.

        Catches and logs:
        - DNS lookup errors
        - Connection timeouts
        - Connection refused errors
        - HTTP errors (with status codes)
        - Generic errors

        This method is called by Scrapy's error handling mechanism
        and is attached to all requests via errback parameter.

        Args:
            failure (twisted.python.failure.Failure): Failure object containing error details
        """
        error_type = failure.type
        request = failure.request
        url = request.url

        try:
            if failure.check(DNSLookupError):
                self.logger.error(f"DNS Lookup Error on {url}")

            elif failure.check(TimeoutError):
                self.logger.error(f"Timeout Error on {url}")

            elif failure.check(ConnectionRefusedError):
                self.logger.error(f"Connection Refused on {url}")

            elif hasattr(failure.value, 'response'):
                response = failure.value.response
                status_code = response.status
                self.logger.error(f"HTTP Error {status_code} on {url}")

            else:
                self.logger.error(f"Error {error_type.__name__} on {url}: {failure.value}")

        except Exception as e:
            self.logger.error(f"Uncaught error on {url}: {str(e)}")

        self.logger.debug(f"Full error trace: {failure.getTraceback()}")

    def closed(self, reason):
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Statistics: {self.stats_data}")
