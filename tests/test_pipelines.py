import sys
import os
import unittest
from unittest.mock import Mock, MagicMock
from scrapy.exceptions import DropItem

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'alkoteka_parser'))

from alkoteka_parser.pipelines import ValidationPipeline, DefaultValuesPipeline, DataCleaningPipeline


class TestValidationPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = ValidationPipeline()
        self.spider = Mock()
        self.spider.logger = Mock()
        self.spider.logger.error = MagicMock()
        self.spider.logger.warning = MagicMock()

    def test_validation_with_all_required_fields(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertIsNotNone(result)
        self.assertEqual(result['product_id'], '12345')

    def test_validation_missing_product_id(self):
        item = {
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890
        }

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_validation_missing_name(self):
        item = {
            'product_id': '12345',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890
        }

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_validation_missing_product_url(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'scraped_at': 1234567890
        }

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_validation_missing_scraped_at(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product'
        }

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_correction_current_price_exceeds_original(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'price_data': {
                'current': 1500,
                'original': 1000,
                'currency': 'RUB'
            }
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['price_data']['current'], 1000)
        self.spider.logger.warning.assert_called()

    def test_correction_negative_stock_count(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'stock_data': {
                'in_stock': False,
                'count': -5,
                'status': 'out of stock'
            }
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['stock_data']['count'], 0)
        self.spider.logger.warning.assert_called()

    def test_correction_price_exceeds_original_price(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'price': 2000.0,
            'original_price': 1500.0
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['price'], 1500.0)


class TestDefaultValuesPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = DefaultValuesPipeline()
        self.spider = Mock()

    def test_default_values_added(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['marketing_tags'], [])
        self.assertEqual(result['attributes'], {})
        self.assertEqual(result['currency'], 'RUB')
        self.assertEqual(result['region'], 'krasnodar')
        self.assertEqual(result['source'], 'alkoteka.com')

    def test_default_values_not_override_existing(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'currency': 'USD',
            'marketing_tags': ['Premium', 'Sale']
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['currency'], 'USD')
        self.assertEqual(result['marketing_tags'], ['Premium', 'Sale'])

    def test_default_scraped_at_timestamp(self):
        import time
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product'
        }

        before = int(time.time())
        result = self.pipeline.process_item(item, self.spider)
        after = int(time.time())

        self.assertIsNotNone(result['scraped_at'])
        self.assertGreaterEqual(result['scraped_at'], before)
        self.assertLessEqual(result['scraped_at'], after)

    def test_default_price_data_currency(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'price_data': {
                'current': 1000,
                'original': 1500
            }
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['price_data']['currency'], 'RUB')
        self.assertIsNone(result['price_data']['sale_tag'])

    def test_default_assets_structure(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'assets': {
                'main_image': None
            }
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertIn('gallery_images', result['assets'])
        self.assertEqual(result['assets']['gallery_images'], [])
        self.assertIn('view_360', result['assets'])
        self.assertEqual(result['assets']['view_360'], [])
        self.assertIn('video', result['assets'])
        self.assertEqual(result['assets']['video'], [])

    def test_default_stock_data_structure(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'stock_data': {
                'in_stock': None
            }
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertIn('count', result['stock_data'])
        self.assertEqual(result['stock_data']['count'], 0)
        self.assertIn('status', result['stock_data'])
        self.assertEqual(result['stock_data']['status'], 'unknown')
        self.assertIn('available_regions', result['stock_data'])
        self.assertEqual(result['stock_data']['available_regions'], [])


class TestDataCleaningPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = DataCleaningPipeline()
        self.spider = Mock()
        self.spider.logger = Mock()
        self.spider.logger.warning = MagicMock()

    def test_clean_whitespace_in_name(self):
        item = {
            'name': '  Vodka   Absolut   Premium  ',
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['name'], 'Vodka Absolut Premium')

    def test_clean_whitespace_in_description(self):
        item = {
            'description': '  This is a   premium   vodka  ',
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['description'], 'This is a premium vodka')

    def test_clean_newlines_in_description(self):
        item = {
            'description': 'Premium vodka\nFine quality\r\nBest choice',
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertNotIn('\n', result['description'])
        self.assertNotIn('\r', result['description'])

    def test_deduplicate_marketing_tags(self):
        item = {
            'marketing_tags': ['Sale', 'Premium', 'Sale', 'Hot Offer', 'Premium'],
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(len(result['marketing_tags']), 3)
        self.assertIn('Sale', result['marketing_tags'])
        self.assertIn('Premium', result['marketing_tags'])
        self.assertIn('Hot Offer', result['marketing_tags'])

    def test_sort_marketing_tags(self):
        item = {
            'marketing_tags': ['Zebra', 'Apple', 'Middle'],
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['marketing_tags'], ['Apple', 'Middle', 'Zebra'])

    def test_clean_attributes_dict(self):
        item = {
            'attributes': {
                'volume': '  750ml  ',
                'origin': '  Russia  ',
                'type': 'Vodka'
            },
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['attributes']['volume'], '750ml')
        self.assertEqual(result['attributes']['origin'], 'Russia')
        self.assertEqual(result['attributes']['type'], 'Vodka')

    def test_deduplicate_image_urls(self):
        item = {
            'image_urls': [
                'https://example.com/img1.jpg',
                'https://example.com/img2.jpg',
                'https://example.com/img1.jpg'
            ],
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(len(result['image_urls']), 2)

    def test_deduplicate_tags(self):
        item = {
            'tags': ['vodka', 'premium', 'vodka', 'russian'],
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(len(result['tags']), 3)
        self.assertEqual(result['tags'], ['premium', 'russian', 'vodka'])

    def test_deduplicate_gallery_images(self):
        item = {
            'assets': {
                'gallery_images': [
                    'https://example.com/img1.jpg',
                    'https://example.com/img2.jpg',
                    'https://example.com/img1.jpg'
                ]
            },
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(len(result['assets']['gallery_images']), 2)

    def test_validate_price_is_positive(self):
        item = {
            'price': -100.0,
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['price'], 0)
        self.spider.logger.warning.assert_called()

    def test_validate_original_price_is_positive(self):
        item = {
            'original_price': -500.0,
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['original_price'], 0)

    def test_validate_rating_range(self):
        item = {
            'rating': 6.5,
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertIsNone(result['rating'])

    def test_validate_discount_percentage_range(self):
        item = {
            'discount_percentage': 150,
            'product_id': '12345',
            'product_url': 'https://example.com',
            'scraped_at': 1234567890
        }

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result['discount_percentage'], 0)


class TestPipelineIntegration(unittest.TestCase):

    def setUp(self):
        self.validation_pipeline = ValidationPipeline()
        self.defaults_pipeline = DefaultValuesPipeline()
        self.cleaning_pipeline = DataCleaningPipeline()
        self.spider = Mock()
        self.spider.logger = Mock()
        self.spider.logger.error = MagicMock()
        self.spider.logger.warning = MagicMock()

    def test_pipeline_chain_execution(self):
        item = {
            'product_id': '12345',
            'name': '  Vodka   Absolut  ',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'marketing_tags': ['Sale', 'Premium', 'Sale'],
            'price': 1200.0,
            'original_price': 1500.0
        }

        result = self.validation_pipeline.process_item(item, self.spider)
        result = self.defaults_pipeline.process_item(result, self.spider)
        result = self.cleaning_pipeline.process_item(result, self.spider)

        self.assertEqual(result['name'], 'Vodka Absolut')
        self.assertEqual(result['currency'], 'RUB')
        self.assertEqual(len(result['marketing_tags']), 2)
        self.assertGreater(result['scraped_at'], 0)

    def test_pipeline_handles_complex_item(self):
        item = {
            'product_id': '12345',
            'name': 'Vodka Absolut',
            'product_url': 'https://example.com/product',
            'scraped_at': 1234567890,
            'price_data': {
                'current': 1000,
                'original': 1500
            },
            'assets': {
                'gallery_images': ['img1.jpg', 'img2.jpg', 'img1.jpg']
            },
            'marketing_tags': ['Premium', 'Sale', 'Premium'],
            'stock_data': {
                'in_stock': True,
                'count': 10
            }
        }

        result = self.validation_pipeline.process_item(item, self.spider)
        result = self.defaults_pipeline.process_item(result, self.spider)
        result = self.cleaning_pipeline.process_item(result, self.spider)

        self.assertEqual(result['product_id'], '12345')
        self.assertEqual(len(result['assets']['gallery_images']), 2)
        self.assertEqual(len(result['marketing_tags']), 2)
        self.assertEqual(result['currency'], 'RUB')


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestValidationPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestDefaultValuesPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestDataCleaningPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    exit(0 if result.wasSuccessful() else 1)
