import scrapy
from typing import Optional, List, Dict, Any
import re
from datetime import datetime

def parse_price(price_string: str) -> Optional[float]:
    if not price_string:
        return None
    cleaned = re.sub(r'[^\d.,]', '', str(price_string).strip())
    cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def calculate_discount(original: float, current: float) -> Optional[int]:
    if not original or not current or original <= 0:
        return None
    discount = ((original - current) / original) * 100
    return int(max(0, min(100, discount)))


def clean_title(title: str) -> str:
    if not title:
        return ""
    title = str(title).strip()
    title = re.sub(r'\s+', ' ', title)
    return title


def extract_number(text: str) -> Optional[int]:
    if not text:
        return None
    match = re.search(r'\d+', str(text))
    return int(match.group()) if match else None


def extract_float(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r'\d+\.?\d*', str(text))
    return float(match.group()) if match else None


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email))) if email else False


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    str_val = str(value).lower().strip()
    return str_val in ('true', 'yes', '1', 'on', 'available', 'in stock')


def validate_required_field(value: Any, field_name: str) -> Any:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Required field '{field_name}' is missing")
    return value


class PriceDataItem(scrapy.Item):
    current = scrapy.Field(
        description="Current selling price in RUB"
    )
    original = scrapy.Field(
        description="Original price before discount"
    )
    sale_tag = scrapy.Field(
        description="Sale tag or discount label (e.g., 'Sale', 'Limited Offer')"
    )
    currency = scrapy.Field(
        description="Currency code (RUB)"
    )


class StockItem(scrapy.Item):
    in_stock = scrapy.Field(
        description="Boolean: True if in stock, False otherwise"
    )
    count = scrapy.Field(
        description="Number of units available"
    )
    status = scrapy.Field(
        description="Stock status text"
    )
    available_regions = scrapy.Field(
        description="List of regions where product is available"
    )


class AssetsItem(scrapy.Item):
    main_image = scrapy.Field(
        description="URL to main product image"
    )
    gallery_images = scrapy.Field(
        description="List of gallery image URLs"
    )
    view_360 = scrapy.Field(
        description="URL to 360-degree view or list of URLs"
    )
    video = scrapy.Field(
        description="URL to product video"
    )
    cached_images = scrapy.Field(
        description="Local file paths of downloaded images"
    )


class ProductItem(scrapy.Item):
    product_id = scrapy.Field(
        description="Unique product ID from Alkoteka website",
        serializer=str
    )
    name = scrapy.Field(
        description="Full product name (brand + product type + volume)",
        serializer=str
    )
    category = scrapy.Field(
        description="Product category (Vodka, Wine, Beer, Whisky, Cognac, etc.)",
        serializer=str
    )
    subcategory = scrapy.Field(
        description="Product subcategory (e.g., Dry, Sweet, Premium)",
        serializer=str
    )

    price_data = scrapy.Field(
        description="Nested PriceDataItem with current, original, sale_tag",
        serializer=dict
    )
    price = scrapy.Field(
        description="Current price in RUB (float)",
        serializer=float
    )
    original_price = scrapy.Field(
        description="Original price before discount (float)",
        serializer=float
    )
    discount_percentage = scrapy.Field(
        description="Discount percentage (0-100) as integer",
        serializer=int
    )
    currency = scrapy.Field(
        description="Currency code (RUB for rubles)",
        serializer=str,
        default="RUB"
    )

    volume = scrapy.Field(
        description="Product volume (e.g., '750ml', '1L', '0.5L')",
        serializer=str
    )
    alcohol_content = scrapy.Field(
        description="Alcohol percentage by volume (e.g., '40%', '12.5%')",
        serializer=str
    )
    product_type = scrapy.Field(
        description="Type of beverage (e.g., Vodka, Cognac, Wine, Beer, Whisky)",
        serializer=str
    )
    brand = scrapy.Field(
        description="Brand/Manufacturer name",
        serializer=str
    )
    country = scrapy.Field(
        description="Country where product is manufactured or from",
        serializer=str
    )
    year = scrapy.Field(
        description="Vintage year (for wines) or production year",
        serializer=str
    )

    description = scrapy.Field(
        description="Detailed product description from store",
        serializer=str
    )
    tasting_notes = scrapy.Field(
        description="Flavor profile and tasting notes",
        serializer=str
    )
    food_pairing = scrapy.Field(
        description="Recommended food pairings",
        serializer=str
    )

    stock_data = scrapy.Field(
        description="Nested StockItem with in_stock, count, status",
        serializer=dict
    )
    in_stock = scrapy.Field(
        description="Boolean flag: True if product is in stock, False otherwise",
        serializer=bool,
        default=True
    )
    stock_quantity = scrapy.Field(
        description="Quantity available in stock",
        serializer=int
    )
    availability_status = scrapy.Field(
        description="Stock status text (e.g., 'In stock', 'Limited', 'Out of stock')",
        serializer=str
    )

    rating = scrapy.Field(
        description="Product rating (1.0 to 5.0 stars)",
        serializer=float
    )
    review_count = scrapy.Field(
        description="Total number of customer reviews",
        serializer=int,
        default=0
    )
    average_rating = scrapy.Field(
        description="Average rating based on customer reviews",
        serializer=float
    )

    assets = scrapy.Field(
        description="Nested AssetsItem with images, video, 360 view",
        serializer=dict
    )
    image_url = scrapy.Field(
        description="URL to product main image",
        serializer=str
    )
    image_urls = scrapy.Field(
        description="List of all product image URLs",
        serializer=list
    )
    images = scrapy.Field(
        description="Local file paths of downloaded images (populated by pipeline)",
        serializer=list
    )

    region = scrapy.Field(
        description="Region/City where product is available (e.g., Krasnodar)",
        serializer=str,
        default="Krasnodar"
    )
    product_url = scrapy.Field(
        description="Direct URL to product page on Alkoteka website",
        serializer=str
    )
    sku = scrapy.Field(
        description="Stock Keeping Unit (if available from store)",
        serializer=str
    )
    barcode = scrapy.Field(
        description="Product barcode (EAN/UPC)",
        serializer=str
    )
    scraped_at = scrapy.Field(
        description="ISO format timestamp when data was scraped",
        serializer=str,
        default=datetime.now().isoformat()
    )
    source = scrapy.Field(
        description="Data source identifier (e.g., 'alkoteka_vodka')",
        serializer=str
    )

    store_id = scrapy.Field(
        description="Specific store/shop ID (if product from particular store)",
        serializer=str
    )
    tags = scrapy.Field(
        description="Product tags (e.g., 'Premium', 'Promotional', 'New')",
        serializer=list,
        default=[]
    )
    attributes = scrapy.Field(
        description="Additional product attributes as key-value pairs",
        serializer=dict,
        default={}
    )
    scraper_notes = scrapy.Field(
        description="Internal notes from scraper (errors, warnings, etc.)",
        serializer=str
    )

    validation_errors = scrapy.Field(
        description="List of validation errors (if any)",
        serializer=list,
        default=[]
    )
    is_valid = scrapy.Field(
        description="Boolean: True if item passed validation",
        serializer=bool,
        default=True
    )


class CategoryItem(scrapy.Item):
    category_id = scrapy.Field(serializer=str)
    name = scrapy.Field(serializer=str)
    description = scrapy.Field(serializer=str)
    url = scrapy.Field(serializer=str)
    product_count = scrapy.Field(serializer=int, default=0)
    parent_category = scrapy.Field(serializer=str)
    image_url = scrapy.Field(serializer=str)
    scraped_at = scrapy.Field(serializer=str, default=datetime.now().isoformat())


class StoreItem(scrapy.Item):
    store_id = scrapy.Field(serializer=str)
    name = scrapy.Field(serializer=str)
    address = scrapy.Field(serializer=str)
    city = scrapy.Field(serializer=str)
    phone = scrapy.Field(serializer=str)
    website = scrapy.Field(serializer=str)
    latitude = scrapy.Field(serializer=float)
    longitude = scrapy.Field(serializer=float)
    scraped_at = scrapy.Field(serializer=str, default=datetime.now().isoformat())


class PriceHistoryItem(scrapy.Item):
    product_id = scrapy.Field(serializer=str)
    price = scrapy.Field(serializer=float)
    discount_percentage = scrapy.Field(serializer=int)
    in_stock = scrapy.Field(serializer=bool)
    region = scrapy.Field(serializer=str)
    timestamp = scrapy.Field(serializer=str, default=datetime.now().isoformat())
    store_id = scrapy.Field(serializer=str)


class ReviewItem(scrapy.Item):
    review_id = scrapy.Field(serializer=str)
    product_id = scrapy.Field(serializer=str)
    rating = scrapy.Field(serializer=int)
    text = scrapy.Field(serializer=str)
    reviewer_name = scrapy.Field(serializer=str)
    date = scrapy.Field(serializer=str)
    helpful_count = scrapy.Field(serializer=int, default=0)
    verified_purchase = scrapy.Field(serializer=bool, default=False)
    scraped_at = scrapy.Field(serializer=str, default=datetime.now().isoformat())


class ErrorItem(scrapy.Item):
    error_id = scrapy.Field(serializer=str)
    error_type = scrapy.Field(serializer=str)
    message = scrapy.Field(serializer=str)
    url = scrapy.Field(serializer=str)
    spider_name = scrapy.Field(serializer=str)
    traceback = scrapy.Field(serializer=str)
    timestamp = scrapy.Field(serializer=str, default=datetime.now().isoformat())
    severity = scrapy.Field(serializer=str, default="INFO")
