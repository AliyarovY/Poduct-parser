import scrapy
from ..item_loaders import ProductItemLoader
from ..items import ProductItem


class AlkotekaProductSpider(scrapy.Spider):
    name = "alkoteka_products"
    allowed_domains = ["alkoteka.com"]
    start_urls = ["https://alkoteka.com/catalog"]

    def parse(self, response):
        for product in response.css('.product-item'):
            loader = ProductItemLoader(item=ProductItem(), selector=product)

            loader.add_css('product_id', '::attr(data-product-id)')
            loader.add_css('name', '.product-name::text')
            loader.add_css('price', '.product-price::text')
            loader.add_css('image_url', '.product-image::attr(src)')
            loader.add_css('category', '::attr(data-category)')

            yield loader.load_item()

        next_page = response.css('a.next-page::attr(href)').get()
        if next_page:
            yield scrapy.Request(next_page, callback=self.parse)


class AlkotekaCategorySpider(scrapy.Spider):
    name = "alkoteka_categories"
    allowed_domains = ["alkoteka.com"]
    start_urls = ["https://alkoteka.com/"]

    custom_settings = {
        'REGION_NAME': 'krasnodar',
    }

    def parse(self, response):
        categories = response.css('.category-link')
        for category in categories:
            yield {
                'name': category.css('::text').get(),
                'url': category.css('::attr(href)').get(),
                'region': self.settings.get('REGION_NAME'),
            }
