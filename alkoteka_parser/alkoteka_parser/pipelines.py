from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from typing import Any, Dict, List, Optional


class ValidationPipeline:
    """
    First-stage pipeline for validating product data integrity.

    Responsibilities:
    - Checks that all required fields are present and non-empty
    - Fixes price contradictions (current price > original price)
    - Validates stock quantity (removes negative values)
    - Drops items that fail validation

    Required fields:
    - product_id: Unique product identifier
    - name: Product name
    - product_url: Link to product page
    - scraped_at: Unix timestamp of scraping

    Priority: 300 (runs first)
    """

    def __init__(self):
        """Initialize validation rules and error tracking."""
        self.required_fields = {
            'product_id': str,
            'name': str,
            'product_url': str,
            'scraped_at': int
        }

        self.validation_errors = []

    def process_item(self, item, spider):
        """
        Validate and correct product item data.

        Args:
            item: Product item from spider
            spider: Scrapy spider instance

        Returns:
            dict: Processed item

        Raises:
            DropItem: If item fails required field validation
        """
        adapter = ItemAdapter(item)
        errors = []

        for field, field_type in self.required_fields.items():
            if field not in adapter or not adapter.get(field):
                errors.append(f"Missing required field: {field}")

        if errors:
            spider.logger.error(f"Item validation failed: {errors}")
            raise DropItem(f"Validation failed: {'; '.join(errors)}")

        if adapter.get('price_data'):
            price_data = adapter['price_data']
            if isinstance(price_data, dict):
                current = price_data.get('current')
                original = price_data.get('original')

                if current is not None and original is not None:
                    if current and original and float(current) > float(original):
                        adapter['price_data'] = {
                            **price_data,
                            'current': original
                        }
                        spider.logger.warning(
                            f"Current price {current} > original {original}, corrected"
                        )

        if adapter.get('stock_data'):
            stock_data = adapter['stock_data']
            if isinstance(stock_data, dict):
                count = stock_data.get('count')
                if count is not None and isinstance(count, (int, float)):
                    if count < 0:
                        adapter['stock_data'] = {
                            **stock_data,
                            'count': 0
                        }
                        spider.logger.warning(
                            f"Negative stock count {count}, set to 0"
                        )

        if adapter.get('price') is not None and adapter.get('original_price') is not None:
            price = float(adapter['price'])
            original = float(adapter['original_price'])
            if price > original:
                adapter['price'] = original
                spider.logger.warning(
                    f"Price {price} > original_price {original}, corrected"
                )

        return item


class DefaultValuesPipeline:
    """
    Second-stage pipeline for setting default values for optional fields.

    Responsibilities:
    - Sets default values for missing optional fields
    - Generates scraped_at timestamp if missing
    - Initializes nested structures (price_data, stock_data, assets)
    - Sets source domain and region information

    Default values:
    - currency: 'RUB'
    - region: 'krasnodar'
    - source: 'alkoteka.com'
    - marketing_tags: []
    - attributes: {}
    - image_urls: []

    Priority: 400 (runs after validation)
    """

    def __init__(self):
        """Initialize default values mapping."""
        self.defaults = {
            'marketing_tags': [],
            'attributes': {},
            'image_urls': [],
            'tags': [],
            'validation_errors': [],
            'scraper_notes': '',
            'is_valid': True,
            'review_count': 0,
            'stock_quantity': 0,
            'currency': 'RUB',
            'region': 'krasnodar',
            'source': 'alkoteka.com'
        }

    def process_item(self, item, spider):
        """
        Set default values for missing fields.

        Args:
            item: Product item from spider
            spider: Scrapy spider instance

        Returns:
            dict: Item with default values set
        """
        adapter = ItemAdapter(item)

        for field, default_value in self.defaults.items():
            if field not in adapter or adapter.get(field) is None:
                if isinstance(default_value, (list, dict)):
                    adapter[field] = default_value.copy() if isinstance(default_value, (list, dict)) else default_value
                else:
                    adapter[field] = default_value

        if adapter.get('scraped_at') is None:
            import time
            adapter['scraped_at'] = int(time.time())

        if adapter.get('price_data'):
            price_data = adapter['price_data']
            if isinstance(price_data, dict):
                if 'currency' not in price_data or not price_data.get('currency'):
                    price_data['currency'] = 'RUB'
                if 'sale_tag' not in price_data:
                    price_data['sale_tag'] = None

        if adapter.get('assets'):
            assets = adapter['assets']
            if isinstance(assets, dict):
                defaults_assets = {
                    'main_image': None,
                    'gallery_images': [],
                    'view_360': [],
                    'video': [],
                    'cached_images': []
                }
                for key, default in defaults_assets.items():
                    if key not in assets or assets.get(key) is None:
                        if isinstance(default, list):
                            assets[key] = []
                        else:
                            assets[key] = default

        if adapter.get('stock_data'):
            stock_data = adapter['stock_data']
            if isinstance(stock_data, dict):
                defaults_stock = {
                    'in_stock': False,
                    'count': 0,
                    'status': 'unknown',
                    'available_regions': []
                }
                for key, default in defaults_stock.items():
                    if key not in stock_data or stock_data.get(key) is None:
                        if isinstance(default, list):
                            stock_data[key] = []
                        else:
                            stock_data[key] = default

        return item


class DataCleaningPipeline:
    """
    Third-stage pipeline for data normalization and cleanup.

    Responsibilities:
    - Normalizes whitespace in string fields
    - Deduplicates and sorts tags and marketing tags
    - Deduplicates image URLs (preserving order)
    - Validates numeric ranges
    - Cleans descriptions by removing extra line breaks

    Operations:
    - String normalization: removes extra spaces, tabs, newlines
    - Tag deduplication: removes duplicates and sorts alphabetically
    - URL deduplication: preserves order of first occurrence
    - Numeric validation: ensures prices, ratings, discounts are in valid ranges

    Priority: 500 (runs last, ensures clean final output)
    """

    def process_item(self, item, spider):
        """
        Clean and normalize product item data.

        Args:
            item: Product item from spider
            spider: Scrapy spider instance

        Returns:
            dict: Cleaned and normalized item
        """
        adapter = ItemAdapter(item)

        string_fields = ['name', 'brand', 'description', 'tasting_notes', 'food_pairing', 'category']
        for field in string_fields:
            if field in adapter and isinstance(adapter.get(field), str):
                cleaned = ' '.join(adapter[field].split())
                if cleaned != adapter[field]:
                    adapter[field] = cleaned

        if adapter.get('marketing_tags') and isinstance(adapter['marketing_tags'], list):
            tags = adapter['marketing_tags']
            cleaned_tags = list(set(tag.strip() for tag in tags if tag and isinstance(tag, str)))
            adapter['marketing_tags'] = sorted(cleaned_tags)

        if adapter.get('attributes') and isinstance(adapter['attributes'], dict):
            attributes = adapter['attributes']
            cleaned_attrs = {}
            for key, value in attributes.items():
                if key and value is not None:
                    if isinstance(value, str):
                        cleaned_value = ' '.join(value.split())
                        cleaned_attrs[key] = cleaned_value
                    elif isinstance(value, list):
                        cleaned_attrs[key] = [v for v in value if v]
                    else:
                        cleaned_attrs[key] = value
            adapter['attributes'] = cleaned_attrs

        if adapter.get('image_urls') and isinstance(adapter['image_urls'], list):
            urls = adapter['image_urls']
            unique_urls = list(dict.fromkeys(urls))
            adapter['image_urls'] = unique_urls

        if adapter.get('tags') and isinstance(adapter['tags'], list):
            tags = adapter['tags']
            unique_tags = list(dict.fromkeys(tag.strip() for tag in tags if tag and isinstance(tag, str)))
            adapter['tags'] = sorted(unique_tags)

        if adapter.get('assets') and isinstance(adapter['assets'], dict):
            assets = adapter['assets']

            if 'gallery_images' in assets and isinstance(assets['gallery_images'], list):
                gallery = assets['gallery_images']
                unique_gallery = list(dict.fromkeys(gallery))
                assets['gallery_images'] = unique_gallery

            if 'view_360' in assets and isinstance(assets['view_360'], list):
                view_360 = assets['view_360']
                unique_360 = list(dict.fromkeys(view_360))
                assets['view_360'] = unique_360

            if 'video' in assets and isinstance(assets['video'], list):
                video = assets['video']
                unique_video = list(dict.fromkeys(video))
                assets['video'] = unique_video

            if 'cached_images' in assets and isinstance(assets['cached_images'], list):
                cached = assets['cached_images']
                unique_cached = list(dict.fromkeys(cached))
                assets['cached_images'] = unique_cached

        if adapter.get('description'):
            desc = adapter['description']
            if isinstance(desc, str):
                cleaned_desc = desc.replace('\r', '').replace('\n', ' ')
                cleaned_desc = ' '.join(cleaned_desc.split())
                adapter['description'] = cleaned_desc

        if adapter.get('price') is not None:
            try:
                price = float(adapter['price'])
                if price < 0:
                    adapter['price'] = 0
                    spider.logger.warning("Negative price set to 0")
            except (ValueError, TypeError):
                adapter['price'] = None

        if adapter.get('original_price') is not None:
            try:
                original = float(adapter['original_price'])
                if original < 0:
                    adapter['original_price'] = 0
                    spider.logger.warning("Negative original_price set to 0")
            except (ValueError, TypeError):
                adapter['original_price'] = None

        if adapter.get('rating') is not None:
            try:
                rating = float(adapter['rating'])
                if rating < 0 or rating > 5:
                    adapter['rating'] = None
                    spider.logger.warning("Invalid rating value, set to None")
            except (ValueError, TypeError):
                adapter['rating'] = None

        if adapter.get('discount_percentage') is not None:
            try:
                discount = int(adapter['discount_percentage'])
                if discount < 0 or discount > 100:
                    adapter['discount_percentage'] = 0
                    spider.logger.warning("Invalid discount percentage, set to 0")
            except (ValueError, TypeError):
                adapter['discount_percentage'] = None

        return item
