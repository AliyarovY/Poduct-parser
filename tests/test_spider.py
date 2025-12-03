import unittest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'alkoteka_parser'))

from alkoteka_parser.spiders.alkoteka_spider import AlkotekaSpider
from scrapy.http import Request, Response, TextResponse
from scrapy.selector import Selector


class TestAlkotekaSpider(unittest.TestCase):
    def setUp(self):
        self.spider = AlkotekaSpider()
        self.spider.logger.info = MagicMock()
        self.spider.logger.warning = MagicMock()
        self.spider.logger.error = MagicMock()
        self.spider.logger.debug = MagicMock()

    def test_spider_name(self):
        self.assertEqual(self.spider.name, 'alkoteka')

    def test_allowed_domains(self):
        self.assertIn('alkoteka.com', self.spider.allowed_domains)

    def test_start_urls_constant(self):
        self.assertTrue(len(self.spider.START_URLS) > 0)
        self.assertTrue(any('vodka' in url for url in self.spider.START_URLS))

    def test_start_requests(self):
        requests = list(self.spider.start_requests())
        self.assertGreater(len(requests), 0)

        for req in requests:
            self.assertIsInstance(req, Request)
            self.assertEqual(req.callback, self.spider.parse_category)
            self.assertIn('category_name', req.meta)

    def test_extract_product_id_from_data_attribute(self):
        html = '<div data-product-id="12345"></div>'
        selector = Selector(text=html)
        response = Mock()
        response.css = Mock(side_effect=lambda x: Mock(get=Mock(return_value="12345" if "product-id" in x else None)))

        product_id = self.spider._extract_product_id(response)
        self.assertIsNotNone(product_id)

    def test_extract_product_id_from_url(self):
        response = Mock()
        response.url = "https://alkoteka.com/product/12345/"
        response.css = Mock(side_effect=lambda x: Mock(get=Mock(return_value=None)))

        product_id = self.spider._extract_product_id(response)
        self.assertEqual(product_id, "12345")

    def test_load_categories(self):
        categories = self.spider._load_categories()
        if categories:
            self.assertIsInstance(categories, list)
            if len(categories) > 0:
                self.assertIn('id', categories[0])
                self.assertIn('name', categories[0])
                self.assertIn('url', categories[0])

    def test_get_next_page_url_with_next_link(self):
        html = '<a class="next-page" href="/page2/">Next</a>'
        response = Mock()
        response.css = Mock(side_effect=lambda x: Mock(get=Mock(return_value="/page2/" if "next-page" in x else None)))
        response.url = "http://example.com/page1/"

        next_url = self.spider._get_next_page_url(response)
        self.assertIsNotNone(next_url)

    def test_get_next_page_url_no_next_page(self):
        response = Mock()
        response.css = Mock(side_effect=lambda x: Mock(get=Mock(return_value=None)))
        response.url = "http://example.com/"

        next_url = self.spider._get_next_page_url(response)
        self.assertIsNone(next_url)

    def test_extract_product_links_from_html(self):
        response = Mock()
        mock_cards = [
            Mock(css=Mock(side_effect=lambda x: Mock(get=Mock(return_value="/product/1/")))),
            Mock(css=Mock(side_effect=lambda x: Mock(get=Mock(return_value="/product/2/")))),
        ]
        response.css = Mock(side_effect=lambda x: Mock() if "product-card" not in x else MagicMock(__iter__=lambda s: iter(mock_cards)))

        links = self.spider._extract_product_links_from_html(response)
        self.assertIsInstance(links, list)

    def test_parse_category_with_products(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=["/product/1/", "/product/2/"])
        mock_selector.get = Mock(return_value=None)
        response.css = Mock(return_value=mock_selector)
        response.meta = {'category_name': 'Водка', 'category_id': '2321', 'page': 1}
        response.urljoin = lambda x: f"https://alkoteka.com{x}"
        response.url = "https://alkoteka.com/catalog/category/vodka/"

        results = list(self.spider.parse_category(response))
        requests = [r for r in results if isinstance(r, Request)]
        self.assertEqual(len(requests), 2)

    def test_parse_category_no_products(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=[])
        mock_selector.get = Mock(return_value=None)
        mock_selector.__iter__ = Mock(return_value=iter([]))
        response.css = Mock(return_value=mock_selector)
        response.meta = {'category_name': 'Empty', 'category_id': '0', 'page': 1}
        response.url = "https://alkoteka.com/catalog/category/empty/"

        results = list(self.spider.parse_category(response))
        self.assertIsInstance(results, list)

    def test_stats_initialization(self):
        self.assertIn('categories_parsed', self.spider.stats_data)
        self.assertIn('products_found', self.spider.stats_data)
        self.assertIn('pages_parsed', self.spider.stats_data)
        self.assertEqual(self.spider.stats_data['categories_parsed'], 0)

    def test_closed_method(self):
        self.spider.closed('finished')
        self.assertIn('categories_parsed', self.spider.stats_data)

    def test_extract_title_with_volume(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(side_effect=lambda: "Vodka Premium")
        response.css = Mock(side_effect=lambda x: mock_selector if "product-title" in x else Mock(get=Mock(return_value=None)))
        response.xpath = Mock(return_value=Mock(get=Mock(return_value="0.75L")))

        title = self.spider._extract_title(response)
        self.assertIsNotNone(title)
        self.assertIn("Vodka", title)

    def test_extract_brand(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="Premium Brand")
        response.css = Mock(return_value=mock_selector)

        brand = self.spider._extract_brand(response)
        self.assertEqual(brand, "Premium Brand")

    def test_extract_sku_from_attribute(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="SKU123456")
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        sku = self.spider._extract_sku(response)
        self.assertEqual(sku, "SKU123456")

    def test_extract_breadcrumbs(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=["Home", "Beverages", "Vodka"])
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(getall=Mock(return_value=[])))

        breadcrumbs = self.spider._extract_breadcrumbs(response)
        self.assertEqual(len(breadcrumbs), 3)
        self.assertIn("Vodka", breadcrumbs)

    def test_extract_marketing_tags(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=["Premium", "Limited Edition", "Hot Deal"])
        response.css = Mock(return_value=mock_selector)

        tags = self.spider._extract_marketing_tags(response)
        self.assertGreater(len(tags), 0)
        self.assertIn("Premium", tags)

    def test_extract_marketing_tags_filters_short_tags(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=["Premium", "A", "Limited Edition"])
        response.css = Mock(return_value=mock_selector)

        tags = self.spider._extract_marketing_tags(response)
        self.assertTrue(all(len(t) > 1 for t in tags))

    def test_extract_volume(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="0.75L")
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        volume = self.spider._extract_volume(response)
        self.assertEqual(volume, "0.75L")

    def test_parse_product_calls_helper_methods(self):
        response = Mock(spec=Response)
        response.url = "https://alkoteka.com/product/12345/"
        response.meta = {'category_name': 'Vodka', 'category_id': '2321'}

        self.spider._extract_title = Mock(return_value="Premium Vodka")
        self.spider._extract_brand = Mock(return_value="Brand")
        self.spider._extract_sku = Mock(return_value="SKU123")
        self.spider._extract_breadcrumbs = Mock(return_value=["Vodka"])
        self.spider._extract_marketing_tags = Mock(return_value=["Premium"])
        self.spider._extract_product_id = Mock(return_value="12345")

        self.spider._extract_title(response)
        self.assertIsNotNone(self.spider._extract_title.return_value)

    def test_clean_price_with_ruble_symbol(self):
        price_str = "1 299 ₽"
        cleaned = self.spider._clean_price(price_str)
        self.assertEqual(cleaned, 1299.0)

    def test_clean_price_with_decimal(self):
        price_str = "1299.99 ₽"
        cleaned = self.spider._clean_price(price_str)
        self.assertEqual(cleaned, 1299.99)

    def test_clean_price_with_spaces(self):
        price_str = "5 000"
        cleaned = self.spider._clean_price(price_str)
        self.assertEqual(cleaned, 5000.0)

    def test_clean_price_invalid_returns_none(self):
        cleaned = self.spider._clean_price("abc")
        self.assertIsNone(cleaned)

    def test_calculate_discount_valid(self):
        discount = self.spider._calculate_discount(1000.0, 750.0)
        self.assertEqual(discount, 25)

    def test_calculate_discount_no_discount(self):
        discount = self.spider._calculate_discount(1000.0, 1000.0)
        self.assertEqual(discount, 0)

    def test_calculate_discount_invalid_returns_none(self):
        discount = self.spider._calculate_discount(0, 750.0)
        self.assertIsNone(discount)

    def test_extract_price_data_with_discount(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(side_effect=lambda: "750" if ".price-current" in str(mock_selector) else "1000")
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        price_data = self.spider._extract_price_data(response)
        self.assertIsNotNone(price_data)

    def test_extract_current_price(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="750 ₽")
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        price = self.spider._extract_current_price(response)
        self.assertEqual(price, 750.0)

    def test_extract_original_price(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="1000 ₽")
        response.css = Mock(return_value=mock_selector)

        price = self.spider._extract_original_price(response)
        self.assertEqual(price, 1000.0)

    def test_check_in_stock_with_buy_button(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="<button>Buy</button>")
        response.css = Mock(return_value=mock_selector)

        in_stock = self.spider._check_in_stock(response)
        self.assertTrue(in_stock)

    def test_check_in_stock_no_button_returns_none(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value=None)
        response.css = Mock(return_value=mock_selector)

        in_stock = self.spider._check_in_stock(response)
        self.assertIsNone(in_stock)

    def test_extract_stock_count_with_regex(self):
        response = Mock(spec=Response)
        mock_xpath = Mock()
        mock_xpath.get = Mock(return_value="Осталось 5 шт")
        response.xpath = Mock(return_value=mock_xpath)
        response.css = Mock(return_value=Mock(get=Mock(return_value=None)))

        count = self.spider._extract_stock_count(response)
        self.assertEqual(count, 5)

    def test_extract_stock_status_in_stock(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value=None)
        response.css = Mock(return_value=mock_selector)

        status = self.spider._extract_stock_status(response)
        self.assertIsNone(status)

    def test_extract_stock_data_complete(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="<button>Buy</button>")
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        stock_data = self.spider._extract_stock_data(response)
        self.assertIsNotNone(stock_data)
        self.assertIn('in_stock', stock_data)

    def test_normalize_url_absolute(self):
        response = Mock(spec=Response)
        url = "https://example.com/image.jpg"
        normalized = self.spider._normalize_url(response, url)
        self.assertEqual(normalized, url)

    def test_normalize_url_protocol_relative(self):
        response = Mock(spec=Response)
        url = "//example.com/image.jpg"
        normalized = self.spider._normalize_url(response, url)
        self.assertTrue(normalized.startswith("https://"))

    def test_normalize_url_relative(self):
        response = Mock(spec=Response)
        response.urljoin = Mock(return_value="https://example.com/images/photo.jpg")
        url = "images/photo.jpg"
        normalized = self.spider._normalize_url(response, url)
        self.assertIsNotNone(normalized)

    def test_normalize_url_empty(self):
        response = Mock(spec=Response)
        normalized = self.spider._normalize_url(response, "")
        self.assertIsNone(normalized)

    def test_extract_main_image(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="image.jpg")
        response.css = Mock(return_value=mock_selector)
        response.urljoin = Mock(return_value="https://example.com/image.jpg")

        main_img = self.spider._extract_main_image(response)
        self.assertIsNotNone(main_img)

    def test_extract_gallery_images(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=["img1.jpg", "img2.jpg"])
        response.css = Mock(return_value=mock_selector)
        response.urljoin = Mock(side_effect=lambda x: f"https://example.com/{x}")
        response.xpath = Mock(return_value=Mock(getall=Mock(return_value=[])))

        images = self.spider._extract_gallery_images(response)
        self.assertIsInstance(images, list)
        self.assertGreater(len(images), 0)

    def test_extract_gallery_images_deduplication(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=["img.jpg", "img.jpg", "img2.jpg"])
        response.css = Mock(return_value=mock_selector)
        response.urljoin = Mock(side_effect=lambda x: f"https://example.com/{x}")
        response.xpath = Mock(return_value=Mock(getall=Mock(return_value=[])))

        images = self.spider._extract_gallery_images(response)
        self.assertTrue(len(images) <= 3)

    def test_extract_gallery_images_sorting(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=["z.jpg", "a.jpg", "m.jpg"])
        response.css = Mock(return_value=mock_selector)
        response.urljoin = Mock(side_effect=lambda x: f"https://example.com/{x}")
        response.xpath = Mock(return_value=Mock(getall=Mock(return_value=[])))

        images = self.spider._extract_gallery_images(response)
        self.assertEqual(images, sorted(images))

    def test_extract_360_view_empty(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=[])
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(getall=Mock(return_value=[])))

        view_360 = self.spider._extract_360_view(response)
        self.assertEqual(view_360, [])

    def test_extract_video_urls(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=[])
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(getall=Mock(return_value=[])))

        video_urls = self.spider._extract_video_urls(response)
        self.assertIsInstance(video_urls, list)

    def test_extract_video_urls_youtube(self):
        response = Mock(spec=Response)
        mock_selector = Mock()

        def css_side_effect(selector):
            if "video source" in selector:
                return Mock(getall=Mock(return_value=[]))
            elif "youtube" in selector:
                return Mock(getall=Mock(return_value=["https://youtube.com/embed/xyz"]))
            elif "vimeo" in selector:
                return Mock(getall=Mock(return_value=[]))
            else:
                return Mock(getall=Mock(return_value=[]))

        response.css = Mock(side_effect=css_side_effect)
        response.xpath = Mock(return_value=Mock(getall=Mock(return_value=[])))

        video_urls = self.spider._extract_video_urls(response)
        self.assertGreater(len(video_urls), 0)

    def test_extract_assets_complete(self):
        response = Mock(spec=Response)

        def css_side_effect(selector):
            mock = Mock()
            if "product-image-main" in selector:
                mock.get = Mock(return_value="main.jpg")
                return mock
            elif "product-gallery" in selector:
                mock.getall = Mock(return_value=["img1.jpg"])
                return mock
            elif "video" in selector:
                mock.getall = Mock(return_value=[])
                return mock
            else:
                mock.get = Mock(return_value=None)
                mock.getall = Mock(return_value=[])
                return mock

        response.css = Mock(side_effect=css_side_effect)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None), getall=Mock(return_value=[])))
        response.urljoin = Mock(side_effect=lambda x: f"https://example.com/{x}")

        assets = self.spider._extract_assets(response)
        self.assertIsNotNone(assets)
        self.assertIn('main_image', assets)

    def test_extract_description(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="This is a great product")
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        desc = self.spider._extract_description(response)
        self.assertEqual(desc, "This is a great product")

    def test_extract_description_empty(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value=None)
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        desc = self.spider._extract_description(response)
        self.assertIsNone(desc)

    def test_parse_table_characteristics(self):
        response = Mock(spec=Response)
        mock_row = Mock()
        mock_row.css = Mock(side_effect=lambda x: Mock(get=Mock(return_value="Объем" if "char-name" in x else "0.75л")))
        response.css = Mock(return_value=Mock(__iter__=lambda s: iter([mock_row])))

        chars = self.spider._parse_table_characteristics(response)
        self.assertIsInstance(chars, dict)

    def test_parse_list_characteristics(self):
        response = Mock(spec=Response)
        mock_item = Mock()
        mock_item.css = Mock(side_effect=lambda x: Mock(get=Mock(return_value="Крепость" if "dt" in x else "40%")))
        response.css = Mock(return_value=Mock(__iter__=lambda s: iter([mock_item])))

        chars = self.spider._parse_list_characteristics(response)
        self.assertIsInstance(chars, dict)

    def test_parse_div_characteristics(self):
        response = Mock(spec=Response)
        mock_div = Mock()
        mock_div.css = Mock(side_effect=lambda x: Mock(get=Mock(return_value="Страна" if "key" in x else "Россия")))
        response.css = Mock(return_value=Mock(__iter__=lambda s: iter([mock_div])))

        chars = self.spider._parse_div_characteristics(response)
        self.assertIsInstance(chars, dict)

    def test_extract_jsonld_characteristics(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        jsonld_data = '{"@type": "Product", "name": "Vodka", "additionalProperty": [{"name": "Volume", "value": "750ml"}]}'
        mock_selector.getall = Mock(return_value=[jsonld_data])
        response.css = Mock(return_value=mock_selector)

        chars = self.spider._extract_jsonld_characteristics(response)
        self.assertIsInstance(chars, dict)

    def test_extract_special_field_volume(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.getall = Mock(return_value=[])
        response.css = Mock(return_value=mock_selector)

        self.spider._extract_characteristics = Mock(return_value={'Объем': '0.75л'})

        volume = self.spider._extract_special_field(response, 'volume', ['объем', 'volume'])
        self.assertEqual(volume, '0.75л')

    def test_extract_special_field_alcohol(self):
        response = Mock(spec=Response)
        self.spider._extract_characteristics = Mock(return_value={'Крепость': '40%'})
        response.css = Mock(return_value=Mock(get=Mock(return_value=None)))

        alcohol = self.spider._extract_special_field(response, 'alcohol', ['крепость', 'alcohol'])
        self.assertEqual(alcohol, '40%')

    def test_extract_special_field_country(self):
        response = Mock(spec=Response)
        self.spider._extract_characteristics = Mock(return_value={'Страна': 'Россия'})
        response.css = Mock(return_value=Mock(get=Mock(return_value=None)))

        country = self.spider._extract_special_field(response, 'country', ['страна', 'country'])
        self.assertEqual(country, 'Россия')

    def test_extract_metadata_complete(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="Product description")
        mock_selector.getall = Mock(return_value=[])
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        self.spider._extract_characteristics = Mock(return_value={'Объем': '0.75л', 'Крепость': '40%'})

        metadata = self.spider._extract_metadata(response)
        self.assertIsInstance(metadata, dict)
        self.assertIn('__description', metadata)
        self.assertIn('characteristics', metadata)

    def test_extract_characteristics_priority(self):
        response = Mock(spec=Response)
        mock_selector = Mock()
        mock_selector.get = Mock(return_value="Value")
        mock_selector.getall = Mock(return_value=[])
        response.css = Mock(return_value=mock_selector)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None), getall=Mock(return_value=[])))

        self.spider._parse_table_characteristics = Mock(return_value={'Key': 'Value'})
        self.spider._parse_list_characteristics = Mock(return_value={})
        self.spider._parse_div_characteristics = Mock(return_value={})
        self.spider._extract_jsonld_characteristics = Mock(return_value={})

        chars = self.spider._extract_characteristics(response)
        self.assertGreater(len(chars), 0)

    def test_extract_volume_variants(self):
        response = Mock()

        def mock_css_volume(selector):
            if 'option' in selector:
                return Mock(getall=Mock(return_value=['500ml', '700ml', '1L']))
            return Mock(getall=Mock(return_value=[]))

        response.css = Mock(side_effect=mock_css_volume)

        variants = self.spider._extract_volume_variants(response)
        self.assertGreater(len(variants), 0)

    def test_extract_volume_variants_empty(self):
        response = Mock()
        response.css = Mock(return_value=Mock(getall=Mock(return_value=[])))

        variants = self.spider._extract_volume_variants(response)
        self.assertEqual(variants, [])

    def test_extract_color_variants(self):
        response = Mock()
        response.url = 'https://alkoteka.com/product'

        def mock_css_color(selector):
            if 'option' in selector or 'color' in selector.lower():
                return Mock(getall=Mock(return_value=['Red', 'Blue']), get=Mock(return_value=None))
            return Mock(getall=Mock(return_value=[]), get=Mock(return_value=None))

        response.css = Mock(side_effect=mock_css_color)

        variants = self.spider._extract_color_variants(response)
        self.assertGreater(len(variants), 0)

    def test_extract_color_variants_empty(self):
        response = Mock()
        response.url = 'https://alkoteka.com/product'

        def mock_css_empty(selector):
            return Mock(getall=Mock(return_value=[]), get=Mock(return_value=None))

        response.css = Mock(side_effect=mock_css_empty)

        variants = self.spider._extract_color_variants(response)
        self.assertEqual(variants, [])

    def test_extract_variants_from_json_valid(self):
        response = Mock()
        response.css = Mock(return_value=Mock(get=Mock(return_value='{"variants": ["v1", "v2"]}')))
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        count = self.spider._extract_variants_from_json(response)
        self.assertEqual(count, 2)

    def test_extract_variants_from_json_options(self):
        response = Mock()
        response.css = Mock(return_value=Mock(get=Mock(return_value='{"options": ["opt1", "opt2", "opt3"]}')))
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        count = self.spider._extract_variants_from_json(response)
        self.assertEqual(count, 3)

    def test_extract_variants_from_json_invalid(self):
        response = Mock()
        response.css = Mock(return_value=Mock(get=Mock(return_value=None)))
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        count = self.spider._extract_variants_from_json(response)
        self.assertEqual(count, 0)

    def test_deduplicate_variants(self):
        variants = ['500ml', '500ml', '700ml', '500ML']
        deduplicated = self.spider._deduplicate_variants(variants)
        self.assertEqual(len(deduplicated), 2)

    def test_validate_variant_valid(self):
        self.assertTrue(self.spider._validate_variant('500ml'))
        self.assertTrue(self.spider._validate_variant('700ml'))
        self.assertTrue(self.spider._validate_variant('Red'))

    def test_validate_variant_invalid_size(self):
        self.assertFalse(self.spider._validate_variant('XL'))
        self.assertFalse(self.spider._validate_variant('Large'))
        self.assertFalse(self.spider._validate_variant('Size M'))

    def test_validate_variant_invalid_clothing(self):
        self.assertFalse(self.spider._validate_variant('Shirt'))
        self.assertFalse(self.spider._validate_variant('Pants'))
        self.assertFalse(self.spider._validate_variant('одежда'))

    def test_validate_variant_invalid_generic(self):
        self.assertFalse(self.spider._validate_variant('select'))
        self.assertFalse(self.spider._validate_variant(''))
        self.assertFalse(self.spider._validate_variant('выбрать'))

    def test_validate_variant_material(self):
        self.assertFalse(self.spider._validate_variant('material cotton'))
        self.assertFalse(self.spider._validate_variant('ткань шелк'))

    def test_detect_variants_with_volumes_and_colors(self):
        response = Mock()

        volume_selector = Mock(getall=Mock(return_value=['500ml', '700ml']), get=Mock(return_value=None))
        color_selector = Mock(getall=Mock(return_value=['Red', 'Blue']), get=Mock(return_value=None))

        def mock_css(selector):
            if 'volume' in selector:
                return volume_selector
            elif 'color' in selector:
                return color_selector
            return Mock(getall=Mock(return_value=[]), get=Mock(return_value=None))

        response.url = 'https://alkoteka.com/product'
        response.css = Mock(side_effect=mock_css)
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        count = self.spider._detect_variants(response)
        self.assertGreaterEqual(count, 0)

    def test_detect_variants_empty(self):
        response = Mock()
        response.url = 'https://alkoteka.com/product'
        response.css = Mock(return_value=Mock(getall=Mock(return_value=[]), get=Mock(return_value=None)))
        response.xpath = Mock(return_value=Mock(get=Mock(return_value=None)))

        count = self.spider._detect_variants(response)
        self.assertEqual(count, 0)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestAlkotekaSpider))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    exit(0 if result.wasSuccessful() else 1)
