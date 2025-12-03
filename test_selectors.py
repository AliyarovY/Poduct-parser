import sys
import json
from scrapy.selector import Selector
import requests
from typing import Optional, Dict, Any


class SelectorDebugger:

    def __init__(self, url: str, timeout: int = 10):
        self.url = url
        self.timeout = timeout
        self.response_text = None
        self.selector = None
        self.results = {}

    def fetch_page(self) -> bool:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=self.timeout)
            response.encoding = 'utf-8'
            self.response_text = response.text
            self.selector = Selector(text=self.response_text)
            print(f"✅ Successfully fetched {self.url}")
            return True
        except requests.RequestException as e:
            print(f"❌ Failed to fetch URL: {e}")
            return False

    def test_selector(self, name: str, selector: str, method: str = 'get') -> Optional[str]:
        if not self.selector:
            print("❌ No selector available. Fetch page first.")
            return None

        try:
            if method == 'get':
                result = self.selector.css(selector).get()
            elif method == 'getall':
                result = self.selector.css(selector).getall()
            elif method == 'xpath':
                result = self.selector.xpath(selector).get()
            else:
                result = None

            self.results[name] = {
                'selector': selector,
                'method': method,
                'result': result,
                'found': result is not None and (isinstance(result, list) and len(result) > 0 or result)
            }

            status = "✅" if self.results[name]['found'] else "❌"
            print(f"{status} {name}: {result}")
            return result

        except Exception as e:
            print(f"❌ Error testing selector '{selector}': {e}")
            self.results[name] = {
                'selector': selector,
                'method': method,
                'error': str(e),
                'found': False
            }
            return None

    def test_product_selectors(self):
        print("\n" + "="*70)
        print("TESTING PRODUCT PAGE SELECTORS")
        print("="*70 + "\n")

        print("📍 Basic Title Selectors:")
        self.test_selector("Title (h1.product-title)", 'h1.product-title::text')
        self.test_selector("Title (h1)", 'h1::text')
        self.test_selector("Title (.product-name)", '.product-name::text')

        print("\n📍 Brand Selectors:")
        self.test_selector("Brand (.product-brand)", '.product-brand::text')
        self.test_selector("Brand (span.brand)", 'span.brand::text')
        self.test_selector("Brand ([data-brand])", '[data-brand]::attr(data-brand)')

        print("\n📍 Price Selectors:")
        self.test_selector("Price (.price)", '.price::text')
        self.test_selector("Price (span.product-price)", 'span.product-price::text')
        self.test_selector("Price ([data-price])", '[data-price]::attr(data-price)')

        print("\n📍 Image Selectors:")
        self.test_selector("Main Image (.product-image img)", '.product-image img::attr(src)')
        self.test_selector("Gallery Images (.gallery img)", '.gallery img::attr(src)', method='getall')
        self.test_selector("Main Image (.main-img)", '.main-img::attr(src)')

        print("\n📍 Stock Selectors:")
        self.test_selector("Stock Status (.stock-status)", '.stock-status::text')
        self.test_selector("In Stock (.in-stock)", '.in-stock::attr(class)')
        self.test_selector("Stock Count ([data-stock])", '[data-stock]::attr(data-stock)')

        print("\n📍 Description Selectors:")
        self.test_selector("Description (.description)", '.description::text')
        self.test_selector("Description (span.desc)", 'span.desc::text')

        print("\n📍 Category/Breadcrumb Selectors:")
        self.test_selector("Breadcrumbs (.breadcrumb a)", '.breadcrumb a::text', method='getall')
        self.test_selector("Category (.category)", '.category::text')

    def test_category_selectors(self):
        print("\n" + "="*70)
        print("TESTING CATEGORY PAGE SELECTORS")
        print("="*70 + "\n")

        print("📍 Product Link Selectors:")
        self.test_selector("Product Links (a.product-link)", 'a.product-link::attr(href)', method='getall')
        self.test_selector("Product Links (.product-card a)", '.product-card a::attr(href)', method='getall')
        self.test_selector("Product Links (.catalog-product a)", '.catalog-product a::attr(href)', method='getall')

        print("\n📍 Pagination Selectors:")
        self.test_selector("Next Page (a.next)", 'a.next::attr(href)')
        self.test_selector("Next Page (.pagination a.next)", '.pagination a.next::attr(href)')
        self.test_selector("Next Page (a[rel=next])", 'a[rel=next]::attr(href)')

    def print_summary(self):
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70 + "\n")

        found = sum(1 for r in self.results.values() if r.get('found'))
        total = len(self.results)

        print(f"✅ Found: {found}/{total}")
        print(f"❌ Not found: {total - found}/{total}\n")

        not_found = [name for name, r in self.results.items() if not r.get('found')]
        if not_found:
            print("Not found selectors:")
            for name in not_found:
                selector = self.results[name]['selector']
                print(f"  • {name}: {selector}")
            print()

    def export_results(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"✅ Results exported to {filepath}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Debug Scrapy selectors')
    parser.add_argument('url', help='URL to test selectors on')
    parser.add_argument('--product', '-p', action='store_true', help='Test product page selectors')
    parser.add_argument('--category', '-c', action='store_true', help='Test category page selectors')
    parser.add_argument('--export', '-e', help='Export results to JSON file')
    parser.add_argument('--timeout', '-t', type=int, default=10, help='Request timeout in seconds')

    args = parser.parse_args()

    if not args.url:
        parser.print_help()
        sys.exit(1)

    debugger = SelectorDebugger(args.url, timeout=args.timeout)

    if not debugger.fetch_page():
        sys.exit(1)

    if args.product:
        debugger.test_product_selectors()
    elif args.category:
        debugger.test_category_selectors()
    else:
        debugger.test_product_selectors()
        debugger.test_category_selectors()

    debugger.print_summary()

    if args.export:
        debugger.export_results(args.export)


if __name__ == '__main__':
    main()
