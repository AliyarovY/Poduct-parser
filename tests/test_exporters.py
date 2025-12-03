"""
Unit tests for custom item exporters.

Tests JSON Lines, CSV, and XML exporters.
"""

import json
import csv
import xml.etree.ElementTree as ET
from io import StringIO
import pytest

from alkoteka_parser.exporters import (
    JsonLinesItemExporter,
    CsvItemExporter,
    XmlItemExporter,
)


class TestJsonLinesItemExporter:
    """Tests for JsonLinesItemExporter."""

    def test_export_single_item(self):
        """Test exporting a single item."""
        output = StringIO()
        exporter = JsonLinesItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка',
            'price': 599.99,
        }

        exporter.export_item(item)

        result = output.getvalue()
        assert result.strip(), "Output should not be empty"

        # Should be valid JSON
        parsed = json.loads(result.strip())
        assert parsed['product_id'] == '123'
        assert parsed['name'] == 'Водка'
        assert parsed['price'] == 599.99

    def test_export_multiple_items(self):
        """Test exporting multiple items."""
        output = StringIO()
        exporter = JsonLinesItemExporter(output)

        items = [
            {'product_id': '1', 'name': 'Водка', 'price': 599.99},
            {'product_id': '2', 'name': 'Коньяк', 'price': 899.99},
            {'product_id': '3', 'name': 'Пиво', 'price': 79.99},
        ]

        for item in items:
            exporter.export_item(item)

        lines = output.getvalue().strip().split('\n')
        assert len(lines) == 3, "Should have 3 lines"

        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed['product_id'] == str(i + 1)

    def test_export_with_nested_structures(self):
        """Test exporting items with nested structures."""
        output = StringIO()
        exporter = JsonLinesItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка',
            'image_urls': ['img1.jpg', 'img2.jpg'],
            'price_data': {
                'current': 599.99,
                'original': 699.99,
                'currency': 'RUB',
            },
        }

        exporter.export_item(item)

        result = output.getvalue().strip()
        parsed = json.loads(result)

        assert isinstance(parsed['image_urls'], list)
        assert len(parsed['image_urls']) == 2
        assert isinstance(parsed['price_data'], dict)
        assert parsed['price_data']['currency'] == 'RUB'

    def test_export_with_special_characters(self):
        """Test exporting items with special characters."""
        output = StringIO()
        exporter = JsonLinesItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка "Премиум"',
            'description': 'Описание с кавычками "тест" и кириллицей',
        }

        exporter.export_item(item)

        result = output.getvalue().strip()
        parsed = json.loads(result)

        assert 'Премиум' in parsed['name']
        assert 'кириллицей' in parsed['description']

    def test_item_count(self):
        """Test item counter."""
        output = StringIO()
        exporter = JsonLinesItemExporter(output)

        assert exporter.item_count == 0

        for i in range(5):
            item = {'product_id': str(i), 'name': f'Product {i}'}
            exporter.export_item(item)

        assert exporter.item_count == 5


class TestCsvItemExporter:
    """Tests for CsvItemExporter."""

    def test_export_single_item(self):
        """Test exporting a single item to CSV."""
        output = StringIO()
        exporter = CsvItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка',
            'price': 599.99,
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()
        lines = result.strip().split('\n')

        # Should have header + 1 data row
        assert len(lines) >= 2, "Should have header and at least one row"

        # Parse CSV
        reader = csv.DictReader(StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['product_id'] == '123'

    def test_export_multiple_items_with_different_fields(self):
        """Test exporting items with varying fields."""
        output = StringIO()
        exporter = CsvItemExporter(output)

        items = [
            {'product_id': '1', 'name': 'Водка', 'price': 599.99},
            {'product_id': '2', 'name': 'Коньяк', 'price': 899.99, 'rating': 4.5},
            {'product_id': '3', 'name': 'Пиво'},
        ]

        for item in items:
            exporter.export_item(item)

        exporter.finish_exporting()

        reader = csv.DictReader(StringIO(output.getvalue()))
        rows = list(reader)

        # All fields from all items should be in header
        assert 'product_id' in reader.fieldnames
        assert 'name' in reader.fieldnames
        assert 'price' in reader.fieldnames
        assert 'rating' in reader.fieldnames

    def test_flatten_nested_structures(self):
        """Test that nested structures are flattened to JSON strings."""
        output = StringIO()
        exporter = CsvItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка',
            'image_urls': ['img1.jpg', 'img2.jpg'],
            'price_data': {'current': 599.99, 'currency': 'RUB'},
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        reader = csv.DictReader(StringIO(output.getvalue()))
        rows = list(reader)

        # Nested structures should be JSON strings
        assert 'img1.jpg' in rows[0]['image_urls']
        assert 'RUB' in rows[0]['price_data']

    def test_flatten_boolean_values(self):
        """Test that boolean values are correctly flattened."""
        output = StringIO()
        exporter = CsvItemExporter(output)

        item = {
            'product_id': '123',
            'in_stock': True,
            'available': False,
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        reader = csv.DictReader(StringIO(output.getvalue()))
        rows = list(reader)

        assert rows[0]['in_stock'] == 'true'
        assert rows[0]['available'] == 'false'

    def test_empty_items(self):
        """Test handling of empty items."""
        output = StringIO()
        exporter = CsvItemExporter(output)

        exporter.finish_exporting()

        result = output.getvalue()
        assert result == '', "Empty exporter should produce empty output"

    def test_field_ordering(self):
        """Test that fields are sorted alphabetically."""
        output = StringIO()
        exporter = CsvItemExporter(output)

        item = {
            'zebra': 'z',
            'apple': 'a',
            'middle': 'm',
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        reader = csv.DictReader(StringIO(output.getvalue()))
        # Fields should be sorted
        assert reader.fieldnames == ['apple', 'middle', 'zebra']


class TestXmlItemExporter:
    """Tests for XmlItemExporter."""

    def test_export_single_item(self):
        """Test exporting a single item to XML."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка',
            'price': 599.99,
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()
        assert '<products' in result
        assert '<product>' in result
        assert '<name>Водка</name>' in result
        assert '<price>599.99</price>' in result

    def test_export_multiple_items(self):
        """Test exporting multiple items to XML."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        items = [
            {'product_id': '1', 'name': 'Водка'},
            {'product_id': '2', 'name': 'Коньяк'},
        ]

        for item in items:
            exporter.export_item(item)

        exporter.finish_exporting()

        result = output.getvalue()
        # Should have two product elements
        assert result.count('<product>') == 2
        assert result.count('</product>') == 2

    def test_export_with_lists(self):
        """Test exporting items with list fields."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка',
            'image_urls': ['img1.jpg', 'img2.jpg', 'img3.jpg'],
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()

        # Lists should be represented as container with items
        assert '<image_urls>' in result
        assert '<item>img1.jpg</item>' in result
        assert '<item>img2.jpg</item>' in result
        assert '<item>img3.jpg</item>' in result

    def test_export_with_nested_dicts(self):
        """Test exporting items with nested dictionaries."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        item = {
            'product_id': '123',
            'price_data': {
                'current': 599.99,
                'original': 699.99,
                'currency': 'RUB',
            },
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()

        # Nested dicts should create nested XML elements
        assert '<price_data>' in result
        assert '<current>599.99</current>' in result
        assert '<currency>RUB</currency>' in result

    def test_sanitize_element_names(self):
        """Test that invalid XML element names are sanitized."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        # Use invalid element names (starting with numbers, spaces, special chars)
        item = {
            '123invalid': 'value1',
            'valid_name': 'value2',
            'name-with-dash': 'value3',
            'name.with.dots': 'value4',
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()

        # All values should be in output even if names are sanitized
        assert 'value1' in result
        assert 'value2' in result
        assert 'value3' in result
        assert 'value4' in result

    def test_boolean_values(self):
        """Test that boolean values are correctly converted."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        item = {
            'product_id': '123',
            'in_stock': True,
            'available': False,
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()

        assert '<in_stock>true</in_stock>' in result
        assert '<available>false</available>' in result

    def test_none_values_ignored(self):
        """Test that None values are ignored."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка',
            'description': None,
            'rating': None,
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()

        # None values should not appear in XML
        assert '<description>' not in result
        assert '<rating>' not in result

    def test_xml_structure(self):
        """Test that exported XML has valid structure."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка',
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()

        # Should be parseable as XML
        try:
            root = ET.fromstring(result)
            assert root.tag == 'products'
            products = root.findall('product')
            assert len(products) == 1
        except ET.ParseError as e:
            pytest.fail(f"Generated invalid XML: {e}")

    def test_special_characters_in_text(self):
        """Test handling of special characters in XML text."""
        output = StringIO()
        exporter = XmlItemExporter(output)

        item = {
            'product_id': '123',
            'name': 'Водка "Премиум"',
            'description': 'Специальные символы: <>&"\'',
        }

        exporter.export_item(item)
        exporter.finish_exporting()

        result = output.getvalue()

        # XML should be valid even with special characters
        try:
            root = ET.fromstring(result)
            # Should be parseable without errors
            assert root is not None
        except ET.ParseError as e:
            pytest.fail(f"Failed to parse XML with special characters: {e}")


class TestExporterIntegration:
    """Integration tests for all exporters."""

    @pytest.fixture
    def sample_items(self):
        """Sample items for testing."""
        return [
            {
                'product_id': '1',
                'name': 'Водка Премиум',
                'price': 599.99,
                'category': 'vodka',
                'image_urls': ['img1.jpg', 'img2.jpg'],
                'in_stock': True,
            },
            {
                'product_id': '2',
                'name': 'Коньяк',
                'price': 899.99,
                'category': 'cognac',
                'image_urls': ['img3.jpg'],
                'in_stock': False,
            },
        ]

    def test_all_exporters_handle_same_items(self, sample_items):
        """Test that all exporters handle the same items without errors."""
        # JSON Lines
        jsonl_output = StringIO()
        jsonl_exporter = JsonLinesItemExporter(jsonl_output)
        for item in sample_items:
            jsonl_exporter.export_item(item)

        # CSV
        csv_output = StringIO()
        csv_exporter = CsvItemExporter(csv_output)
        for item in sample_items:
            csv_exporter.export_item(item)
        csv_exporter.finish_exporting()

        # XML
        xml_output = StringIO()
        xml_exporter = XmlItemExporter(xml_output)
        for item in sample_items:
            xml_exporter.export_item(item)
        xml_exporter.finish_exporting()

        # All should produce non-empty output
        assert len(jsonl_output.getvalue()) > 0
        assert len(csv_output.getvalue()) > 0
        assert len(xml_output.getvalue()) > 0

    def test_consistency_across_formats(self, sample_items):
        """Test that key data is consistent across all formats."""
        # Export to all formats
        jsonl_output = StringIO()
        jsonl_exporter = JsonLinesItemExporter(jsonl_output)

        csv_output = StringIO()
        csv_exporter = CsvItemExporter(csv_output)

        xml_output = StringIO()
        xml_exporter = XmlItemExporter(xml_output)

        for item in sample_items:
            jsonl_exporter.export_item(item)
            csv_exporter.export_item(item)
            xml_exporter.export_item(item)

        csv_exporter.finish_exporting()
        xml_exporter.finish_exporting()

        # Verify each format has the data
        jsonl_lines = jsonl_output.getvalue().strip().split('\n')
        assert len(jsonl_lines) == 2

        csv_reader = csv.DictReader(StringIO(csv_output.getvalue()))
        csv_rows = list(csv_reader)
        assert len(csv_rows) == 2

        # All should contain product IDs
        jsonl_ids = [json.loads(line)['product_id'] for line in jsonl_lines]
        csv_ids = [row['product_id'] for row in csv_rows]

        assert '1' in jsonl_ids and '2' in jsonl_ids
        assert '1' in csv_ids and '2' in csv_ids
