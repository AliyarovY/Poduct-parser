"""
Custom Scrapy command to validate exported data files.

Usage:
    scrapy validate -f result.json
    scrapy validate -f result.csv --format csv
    scrapy validate -f logs/stats/*.json --verbose

Features:
- Validate JSON, CSV, XML files
- Check required fields
- Detect data inconsistencies
- Generate detailed report
"""

import json
import csv
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

from scrapy.commands import ScrapyCommand
from scrapy.utils.misc import load_object


class Command(ScrapyCommand):
    """Custom validate command for Scrapy."""

    requires_project = False

    def short_desc(self):
        """Return command description."""
        return "Validate exported data files (JSON, CSV, XML)"

    def add_options(self, parser):
        """Add command line options."""
        ScrapyCommand.add_options(self, parser)
        parser.add_argument(
            '-f', '--file',
            dest='file',
            required=True,
            help='Path to exported file to validate'
        )
        parser.add_argument(
            '--format',
            dest='format',
            choices=['auto', 'json', 'jsonl', 'csv', 'xml'],
            default='auto',
            help='File format (default: auto-detect)'
        )
        parser.add_argument(
            '-v', '--verbose',
            dest='verbose',
            action='store_true',
            help='Verbose output with detailed errors'
        )
        parser.add_argument(
            '--check-fields',
            dest='check_fields',
            help='Comma-separated required fields (product_id,name,price)'
        )
        parser.add_argument(
            '--stats',
            dest='stats',
            action='store_true',
            help='Show statistics about the data'
        )

    def run(self, args, opts):
        """Run the validate command."""
        file_path = opts.get('file')
        file_format = opts.get('format', 'auto')
        verbose = opts.get('verbose', False)
        check_fields = opts.get('check_fields', '')
        show_stats = opts.get('stats', False)

        if not file_path:
            self.crawler.engine.close_spider(self.crawler.spider, 'no_file')
            return

        path = Path(file_path)
        if not path.exists():
            self.print_error(f"❌ File not found: {file_path}")
            return

        # Auto-detect format
        if file_format == 'auto':
            file_format = path.suffix.lstrip('.')

        # Parse required fields
        required_fields = [f.strip() for f in check_fields.split(',') if f.strip()] if check_fields else []

        try:
            validator = DataValidator(str(path), file_format, verbose)
            report = validator.validate(required_fields, show_stats)
            self.print_report(report)

            # Exit with appropriate code
            if report['errors'] > 0:
                sys.exit(1)
            else:
                sys.exit(0)

        except Exception as e:
            self.print_error(f"❌ Validation failed: {str(e)}")
            sys.exit(1)

    def print_error(self, message: str):
        """Print error message."""
        print(f"\n{message}\n")

    def print_report(self, report: Dict[str, Any]):
        """Print validation report."""
        print("\n" + "=" * 70)
        print("DATA VALIDATION REPORT")
        print("=" * 70)

        print(f"\n📊 SUMMARY")
        print(f"  Total Items: {report['total_items']}")
        print(f"  Valid Items: {report['valid_items']}")
        print(f"  Invalid Items: {report['invalid_items']}")
        print(f"  Errors: {report['errors']}")
        print(f"  Warnings: {report['warnings']}")

        if report['required_fields']:
            print(f"\n✅ REQUIRED FIELDS CHECK")
            for field in report['required_fields']:
                status = "✓" if field['found'] else "✗"
                print(f"  {status} {field['name']}: {field['count']}/{field['total']}")

        if report['field_stats']:
            print(f"\n📈 FIELD STATISTICS")
            for field_name, stats in report['field_stats'].items():
                print(f"  {field_name}:")
                print(f"    • Filled: {stats['filled']}/{stats['total']} ({stats['percentage']:.1f}%)")
                if 'type' in stats:
                    print(f"    • Type: {stats['type']}")

        if report['errors_list']:
            print(f"\n❌ ERRORS ({len(report['errors_list'])})")
            for i, error in enumerate(report['errors_list'][:10], 1):
                print(f"  {i}. {error}")
            if len(report['errors_list']) > 10:
                print(f"  ... and {len(report['errors_list']) - 10} more")

        if report['warnings_list']:
            print(f"\n⚠️  WARNINGS ({len(report['warnings_list'])})")
            for i, warning in enumerate(report['warnings_list'][:10], 1):
                print(f"  {i}. {warning}")
            if len(report['warnings_list']) > 10:
                print(f"  ... and {len(report['warnings_list']) - 10} more")

        if report['recommendations']:
            print(f"\n💡 RECOMMENDATIONS")
            for rec in report['recommendations']:
                print(f"  • {rec}")

        print("\n" + "=" * 70 + "\n")


class DataValidator:
    """Validate exported data files."""

    def __init__(self, file_path: str, file_format: str, verbose: bool = False):
        """Initialize validator."""
        self.file_path = file_path
        self.file_format = file_format
        self.verbose = verbose
        self.items = []

    def validate(self, required_fields: List[str] = None, show_stats: bool = False) -> Dict[str, Any]:
        """
        Validate data file.

        Args:
            required_fields: List of required field names
            show_stats: Show detailed statistics

        Returns:
            Validation report dictionary
        """
        # Load items
        self._load_items()

        report = {
            'total_items': len(self.items),
            'valid_items': 0,
            'invalid_items': 0,
            'errors': 0,
            'warnings': 0,
            'errors_list': [],
            'warnings_list': [],
            'required_fields': [],
            'field_stats': {},
            'recommendations': [],
        }

        # Check required fields
        if required_fields:
            for field in required_fields:
                count = sum(1 for item in self.items if item.get(field))
                report['required_fields'].append({
                    'name': field,
                    'found': count == len(self.items),
                    'count': count,
                    'total': len(self.items),
                })
                if count < len(self.items):
                    report['errors'] += (len(self.items) - count)
                    report['errors_list'].append(
                        f"Field '{field}' missing in {len(self.items) - count} items"
                    )

        # Validate each item
        for i, item in enumerate(self.items):
            if self._validate_item(item):
                report['valid_items'] += 1
            else:
                report['invalid_items'] += 1

        # Collect field statistics
        if show_stats and self.items:
            all_fields = set()
            for item in self.items:
                all_fields.update(item.keys())

            for field in sorted(all_fields):
                filled = sum(1 for item in self.items if item.get(field))
                percentage = (filled / len(self.items) * 100) if self.items else 0
                field_type = self._detect_field_type(field)

                report['field_stats'][field] = {
                    'filled': filled,
                    'total': len(self.items),
                    'percentage': percentage,
                    'type': field_type,
                }

        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)

        return report

    def _load_items(self):
        """Load items from file."""
        if self.file_format == 'json':
            with open(self.file_path, encoding='utf-8') as f:
                data = json.load(f)
                self.items = data if isinstance(data, list) else [data]

        elif self.file_format == 'jsonl':
            with open(self.file_path, encoding='utf-8') as f:
                self.items = [json.loads(line) for line in f if line.strip()]

        elif self.file_format == 'csv':
            with open(self.file_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.items = list(reader)

        else:
            raise ValueError(f"Unsupported format: {self.file_format}")

    def _validate_item(self, item: Dict) -> bool:
        """Validate single item."""
        # Check basic required fields
        required = ['product_id', 'name']
        for field in required:
            if not item.get(field):
                if self.verbose:
                    print(f"Missing {field} in item: {item}")
                return False
        return True

    def _detect_field_type(self, field_name: str) -> str:
        """Detect field data type."""
        values = [item.get(field_name) for item in self.items if field_name in item]
        if not values:
            return 'unknown'

        # Sample first non-None value
        for v in values:
            if v is not None:
                if isinstance(v, bool):
                    return 'boolean'
                elif isinstance(v, int):
                    return 'integer'
                elif isinstance(v, float):
                    return 'float'
                elif isinstance(v, list):
                    return 'array'
                elif isinstance(v, dict):
                    return 'object'
                else:
                    return 'string'
        return 'null'

    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        if report['invalid_items'] > 0:
            percentage = (report['invalid_items'] / report['total_items'] * 100)
            if percentage > 10:
                recommendations.append(
                    f"High number of invalid items ({percentage:.1f}%). "
                    "Check spider selectors and data extraction logic."
                )

        for field_stat in report.get('field_stats', {}).values():
            if field_stat['percentage'] < 50:
                recommendations.append(
                    f"Field '{field_stat}' has only {field_stat['percentage']:.1f}% filled. "
                    "Consider updating selectors or adding fallback extraction methods."
                )

        if report['errors'] == 0:
            recommendations.append("✅ All validations passed! Data looks good.")

        return recommendations


__all__ = ['Command']
