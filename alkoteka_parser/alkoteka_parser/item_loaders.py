from scrapy.loader import ItemLoader
from itemloaders.processors import MapCompose, TakeFirst, Compose, Identity, Join
from .items import (
    ProductItem,
    CategoryItem,
    StoreItem,
    PriceHistoryItem,
    ReviewItem,
    ErrorItem,
    PriceDataItem,
    StockItem,
    AssetsItem,
)
from .items import (
    parse_price,
    calculate_discount,
    clean_title,
    extract_number,
    extract_float,
    normalize_bool,
)


class FirstValue:
    def __call__(self, values):
        return values[0] if values else None


class FloatValue:
    def __call__(self, values):
        if not values:
            return None
        try:
            return float(values[0])
        except (ValueError, TypeError):
            return None


class IntValue:
    def __call__(self, values):
        if not values:
            return None
        try:
            return int(values[0])
        except (ValueError, TypeError):
            return None


class BoolValue:
    def __call__(self, values):
        if not values:
            return False
        return normalize_bool(values[0])


class ProductItemLoader(ItemLoader):
    default_item_class = ProductItem
    default_output_processor = TakeFirst()

    product_id_in = MapCompose(str.strip)
    product_id_out = TakeFirst()

    name_in = MapCompose(clean_title)
    name_out = TakeFirst()

    category_in = MapCompose(str.strip)
    category_out = TakeFirst()

    subcategory_in = MapCompose(str.strip)
    subcategory_out = TakeFirst()

    price_in = MapCompose(parse_price)
    price_out = FloatValue()

    original_price_in = MapCompose(parse_price)
    original_price_out = FloatValue()

    discount_percentage_in = MapCompose(extract_number)
    discount_percentage_out = IntValue()

    currency_in = MapCompose(str.strip)
    currency_out = Compose(TakeFirst(), lambda x: x or "RUB")

    volume_in = MapCompose(str.strip)
    volume_out = TakeFirst()

    alcohol_content_in = MapCompose(extract_float)
    alcohol_content_out = FloatValue()

    product_type_in = MapCompose(str.strip)
    product_type_out = TakeFirst()

    brand_in = MapCompose(clean_title)
    brand_out = TakeFirst()

    country_in = MapCompose(str.strip)
    country_out = TakeFirst()

    year_in = MapCompose(extract_number)
    year_out = Compose(IntValue(), lambda x: str(x) if x else None)

    description_in = MapCompose(str.strip)
    description_out = TakeFirst()

    tasting_notes_in = MapCompose(str.strip)
    tasting_notes_out = TakeFirst()

    food_pairing_in = MapCompose(str.strip)
    food_pairing_out = TakeFirst()

    in_stock_in = MapCompose(normalize_bool)
    in_stock_out = BoolValue()

    stock_quantity_in = MapCompose(extract_number)
    stock_quantity_out = IntValue()

    availability_status_in = MapCompose(str.strip)
    availability_status_out = TakeFirst()

    rating_in = MapCompose(extract_float)
    rating_out = FloatValue()

    review_count_in = MapCompose(extract_number)
    review_count_out = IntValue()

    average_rating_in = MapCompose(extract_float)
    average_rating_out = FloatValue()

    image_url_in = MapCompose(str.strip)
    image_url_out = TakeFirst()

    image_urls_in = Identity()
    image_urls_out = Identity()

    images_in = Identity()
    images_out = Identity()

    region_in = MapCompose(str.strip)
    region_out = Compose(TakeFirst(), lambda x: x or "Krasnodar")

    product_url_in = MapCompose(str.strip)
    product_url_out = TakeFirst()

    sku_in = MapCompose(str.strip)
    sku_out = TakeFirst()

    barcode_in = MapCompose(str.strip)
    barcode_out = TakeFirst()

    source_in = MapCompose(str.strip)
    source_out = TakeFirst()

    scraped_at_in = MapCompose(str.strip)
    scraped_at_out = TakeFirst()

    store_id_in = MapCompose(str.strip)
    store_id_out = TakeFirst()

    tags_in = Identity()
    tags_out = Identity()

    attributes_in = Identity()
    attributes_out = Compose(TakeFirst(), lambda x: x or {})

    scraper_notes_in = MapCompose(str.strip)
    scraper_notes_out = TakeFirst()

    validation_errors_in = Identity()
    validation_errors_out = Compose(TakeFirst(), lambda x: x or [])

    is_valid_in = MapCompose(normalize_bool)
    is_valid_out = BoolValue()


class PriceDataItemLoader(ItemLoader):
    default_item_class = PriceDataItem
    default_output_processor = TakeFirst()

    current_in = MapCompose(parse_price)
    current_out = FloatValue()

    original_in = MapCompose(parse_price)
    original_out = FloatValue()

    sale_tag_in = MapCompose(str.strip)
    sale_tag_out = TakeFirst()

    currency_in = MapCompose(str.strip)
    currency_out = Compose(TakeFirst(), lambda x: x or "RUB")


class StockItemLoader(ItemLoader):
    default_item_class = StockItem
    default_output_processor = TakeFirst()

    in_stock_in = MapCompose(normalize_bool)
    in_stock_out = BoolValue()

    count_in = MapCompose(extract_number)
    count_out = IntValue()

    status_in = MapCompose(str.strip)
    status_out = TakeFirst()

    available_regions_in = Identity()
    available_regions_out = Identity()


class AssetsItemLoader(ItemLoader):
    default_item_class = AssetsItem
    default_output_processor = TakeFirst()

    main_image_in = MapCompose(str.strip)
    main_image_out = TakeFirst()

    gallery_images_in = Identity()
    gallery_images_out = Identity()

    view_360_in = Identity()
    view_360_out = TakeFirst()

    video_in = MapCompose(str.strip)
    video_out = TakeFirst()

    cached_images_in = Identity()
    cached_images_out = Identity()


class CategoryItemLoader(ItemLoader):
    default_item_class = CategoryItem
    default_output_processor = TakeFirst()

    category_id_in = MapCompose(str.strip)
    category_id_out = TakeFirst()

    name_in = MapCompose(clean_title)
    name_out = TakeFirst()

    description_in = MapCompose(str.strip)
    description_out = TakeFirst()

    url_in = MapCompose(str.strip)
    url_out = TakeFirst()

    product_count_in = MapCompose(extract_number)
    product_count_out = IntValue()

    parent_category_in = MapCompose(str.strip)
    parent_category_out = TakeFirst()

    image_url_in = MapCompose(str.strip)
    image_url_out = TakeFirst()


class StoreItemLoader(ItemLoader):
    default_item_class = StoreItem
    default_output_processor = TakeFirst()

    store_id_in = MapCompose(str.strip)
    store_id_out = TakeFirst()

    name_in = MapCompose(clean_title)
    name_out = TakeFirst()

    address_in = MapCompose(str.strip)
    address_out = TakeFirst()

    city_in = MapCompose(str.strip)
    city_out = TakeFirst()

    phone_in = MapCompose(str.strip)
    phone_out = TakeFirst()

    website_in = MapCompose(str.strip)
    website_out = TakeFirst()

    latitude_in = MapCompose(extract_float)
    latitude_out = FloatValue()

    longitude_in = MapCompose(extract_float)
    longitude_out = FloatValue()


class PriceHistoryItemLoader(ItemLoader):
    default_item_class = PriceHistoryItem
    default_output_processor = TakeFirst()

    product_id_in = MapCompose(str.strip)
    product_id_out = TakeFirst()

    price_in = MapCompose(parse_price)
    price_out = FloatValue()

    discount_percentage_in = MapCompose(extract_number)
    discount_percentage_out = IntValue()

    in_stock_in = MapCompose(normalize_bool)
    in_stock_out = BoolValue()

    region_in = MapCompose(str.strip)
    region_out = TakeFirst()

    store_id_in = MapCompose(str.strip)
    store_id_out = TakeFirst()


class ReviewItemLoader(ItemLoader):
    default_item_class = ReviewItem
    default_output_processor = TakeFirst()

    review_id_in = MapCompose(str.strip)
    review_id_out = TakeFirst()

    product_id_in = MapCompose(str.strip)
    product_id_out = TakeFirst()

    rating_in = MapCompose(extract_number)
    rating_out = IntValue()

    text_in = MapCompose(str.strip)
    text_out = TakeFirst()

    reviewer_name_in = MapCompose(clean_title)
    reviewer_name_out = TakeFirst()

    date_in = MapCompose(str.strip)
    date_out = TakeFirst()

    helpful_count_in = MapCompose(extract_number)
    helpful_count_out = IntValue()

    verified_purchase_in = MapCompose(normalize_bool)
    verified_purchase_out = BoolValue()


class ErrorItemLoader(ItemLoader):
    default_item_class = ErrorItem
    default_output_processor = TakeFirst()

    error_id_in = MapCompose(str.strip)
    error_id_out = TakeFirst()

    error_type_in = MapCompose(str.strip)
    error_type_out = TakeFirst()

    message_in = MapCompose(str.strip)
    message_out = TakeFirst()

    url_in = MapCompose(str.strip)
    url_out = TakeFirst()

    spider_name_in = MapCompose(str.strip)
    spider_name_out = TakeFirst()

    traceback_in = MapCompose(str.strip)
    traceback_out = TakeFirst()

    severity_in = MapCompose(str.strip)
    severity_out = Compose(TakeFirst(), lambda x: x or "INFO")
