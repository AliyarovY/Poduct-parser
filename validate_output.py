import json
import sys
from typing import Any, Dict, List
from urllib.parse import urlparse


class OutputValidator:

    REQUIRED_FIELDS = [
        'product_id',
        'name',
        'product_url',
        'scraped_at',
    ]

    NUMERIC_FIELDS = {
        'price': (float, int),
        'original_price': (float, int),
        'rating': (float, int),
        'review_count': int,
        'stock_quantity': int,
        'discount_percentage': int,
        'scraped_at': int,
    }

    URL_FIELDS = [
        'product_url',
        'image_url',
    ]

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.products = []
        self.errors = []
        self.warnings = []
        self.stats = {
            'total_products': 0,
            'valid_products': 0,
            'invalid_products': 0,
            'errors': 0,
            'warnings': 0,
        }

    def load_json(self) -> bool:
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.products = json.load(f)
            return True
        except FileNotFoundError:
            self.errors.append(f"File not found: {self.filepath}")
            return False
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {str(e)}")
            return False

    def validate_url(self, url: str) -> bool:
        if not url:
            return False
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def validate_product(self, product: Dict[str, Any], index: int) -> bool:
        is_valid = True

        for field in self.REQUIRED_FIELDS:
            if field not in product or not product.get(field):
                self.errors.append(f"Product {index}: Missing required field '{field}'")
                is_valid = False
                self.stats['errors'] += 1

        for field, expected_type in self.NUMERIC_FIELDS.items():
            if field in product and product[field] is not None:
                value = product[field]
                if not isinstance(value, expected_type):
                    self.warnings.append(
                        f"Product {index}: Field '{field}' has type {type(value).__name__}, expected {expected_type}"
                    )
                    self.stats['warnings'] += 1

                if isinstance(expected_type, tuple):
                    if any(value < 0 for _ in [None]):
                        if field not in ('rating',):
                            if value < 0:
                                self.warnings.append(f"Product {index}: Field '{field}' is negative: {value}")
                                self.stats['warnings'] += 1

        for field in self.URL_FIELDS:
            if field in product and product[field]:
                if not self.validate_url(product[field]):
                    self.warnings.append(f"Product {index}: Field '{field}' has invalid URL: {product[field]}")
                    self.stats['warnings'] += 1

        if product.get('price') and product.get('original_price'):
            price = float(product['price'])
            original = float(product['original_price'])
            if price > original:
                self.warnings.append(
                    f"Product {index}: Price ({price}) > original_price ({original})"
                )
                self.stats['warnings'] += 1

        if product.get('marketing_tags'):
            if not isinstance(product['marketing_tags'], list):
                self.warnings.append(f"Product {index}: 'marketing_tags' should be a list")
                self.stats['warnings'] += 1

        if product.get('image_urls'):
            if not isinstance(product['image_urls'], list):
                self.warnings.append(f"Product {index}: 'image_urls' should be a list")
                self.stats['warnings'] += 1

        return is_valid

    def validate_all(self) -> bool:
        if not self.products:
            self.errors.append("No products to validate")
            return False

        self.stats['total_products'] = len(self.products)

        for index, product in enumerate(self.products):
            if self.validate_product(product, index):
                self.stats['valid_products'] += 1
            else:
                self.stats['invalid_products'] += 1

        return self.stats['errors'] == 0

    def print_report(self):
        print("\n" + "="*70)
        print("VALIDATION REPORT")
        print("="*70 + "\n")

        print(f"📊 STATISTICS")
        print(f"  Total Products:    {self.stats['total_products']}")
        print(f"  Valid Products:    {self.stats['valid_products']}")
        print(f"  Invalid Products:  {self.stats['invalid_products']}")
        print(f"  Total Errors:      {self.stats['errors']}")
        print(f"  Total Warnings:    {self.stats['warnings']}\n")

        if self.errors:
            print(f"❌ ERRORS ({len(self.errors)})")
            for error in self.errors[:10]:
                print(f"  • {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors\n")
            else:
                print()

        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)})")
            for warning in self.warnings[:10]:
                print(f"  • {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more warnings\n")
            else:
                print()

        if not self.errors and not self.warnings:
            print("✅ All validations passed!\n")

        print("="*70 + "\n")

    def get_sample_product(self) -> Dict[str, Any]:
        if self.products:
            return self.products[0]
        return {}


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Validate Scrapy output JSON')
    parser.add_argument('file', help='Path to JSON file to validate')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show sample product')
    args = parser.parse_args()

    validator = OutputValidator(args.file)

    if not validator.load_json():
        print("❌ Failed to load JSON file")
        for error in validator.errors:
            print(f"  {error}")
        sys.exit(1)

    validator.validate_all()
    validator.print_report()

    if args.verbose:
        sample = validator.get_sample_product()
        if sample:
            print("📋 SAMPLE PRODUCT")
            print(json.dumps(sample, indent=2, ensure_ascii=False))
            print()

    sys.exit(0 if validator.stats['errors'] == 0 else 1)


if __name__ == '__main__':
    main()
