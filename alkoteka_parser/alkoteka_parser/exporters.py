"""
Custom data exporters for Alkaloteka products.

Supports multiple output formats:
- JSON Lines (.jsonl) - один JSON объект на строку
- CSV (.csv) - табулярный формат с заголовками
- XML (.xml) - XML с валидированной структурой

Usage:
    # JSON Lines (по умолчанию)
    scrapy crawl alkoteka -O result.jsonl

    # CSV
    scrapy crawl alkoteka -O result.csv

    # XML
    scrapy crawl alkoteka -O result.xml

    # Изменить экспортер через settings.py
    FEED_EXPORTERS = {
        'jsonl': 'alkoteka_parser.exporters.JsonLinesItemExporter',
        'csv': 'alkoteka_parser.exporters.CsvItemExporter',
        'xml': 'alkoteka_parser.exporters.XmlItemExporter',
    }
"""

import json
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from io import StringIO
from typing import Any, Dict, List

from scrapy.exporters import BaseItemExporter


class JsonLinesItemExporter(BaseItemExporter):
    """
    Экспортер для JSON Lines формата (JSONL).

    Каждый товар - это отдельная строка с полным JSON объектом.
    Удобен для потоковой обработки и работы с большими датасетами.

    Пример:
        {"product_id": "123", "name": "Водка", "price": 599.99}
        {"product_id": "124", "name": "Коньяк", "price": 899.99}
    """

    def __init__(self, file, **kwargs):
        super().__init__(**kwargs)
        self.file = file
        self.item_count = 0

    def export_item(self, item):
        """Экспортирует один товар как JSON строку."""
        itemdict = dict(self._get_serialized_fields(item))
        self.file.write(json.dumps(itemdict, ensure_ascii=False, default=str) + '\n')
        self.item_count += 1

    def finish_exporting(self):
        """Завершает экспорт и выводит статистику."""
        pass


class CsvItemExporter(BaseItemExporter):
    """
    Экспортер для CSV формата.

    Преобразует товары в табулярный формат с заголовками.
    Все поля переводятся в плоскую структуру (вложенные объекты сериализуются в JSON).

    Пример:
        product_id,name,price,image_urls
        123,Водка,599.99,"['img1.jpg', 'img2.jpg']"
        124,Коньяк,899.99,"['img3.jpg']"
    """

    def __init__(self, file, **kwargs):
        super().__init__(**kwargs)
        self.file = file
        self.writer = None
        self.fieldnames = set()
        self.items = []

    def export_item(self, item):
        """Собирает товары для последующей записи."""
        itemdict = dict(self._get_serialized_fields(item))
        self.fieldnames.update(itemdict.keys())
        self.items.append(itemdict)

    def _flatten_value(self, value: Any) -> str:
        """
        Преобразует значение в CSV-совместимый формат.

        Args:
            value: Значение для преобразования

        Returns:
            Строковое представление значения
        """
        if value is None:
            return ''
        elif isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False, default=str)
        elif isinstance(value, bool):
            return 'true' if value else 'false'
        else:
            return str(value)

    def finish_exporting(self):
        """Записывает все собранные товары в CSV."""
        if not self.items:
            return

        # Сортируем поля для консистентности
        fieldnames = sorted(self.fieldnames)

        # Создаём CSV writer
        self.writer = csv.DictWriter(
            self.file,
            fieldnames=fieldnames,
            extrasaction='ignore',
            quoting=csv.QUOTE_MINIMAL,
            quotechar='"',
            escapechar='\\',
        )

        # Пишем заголовок
        self.writer.writeheader()

        # Пишем данные
        for item in self.items:
            row = {key: self._flatten_value(item.get(key)) for key in fieldnames}
            self.writer.writerow(row)


class XmlItemExporter(BaseItemExporter):
    """
    Экспортер для XML формата.

    Создаёт XML структуру с корневым элементом 'products'
    и вложенными элементами 'product' для каждого товара.

    Пример:
        <?xml version="1.0" encoding="UTF-8"?>
        <products>
            <product>
                <product_id>123</product_id>
                <name>Водка</name>
                <price>599.99</price>
                <image_urls>
                    <url>img1.jpg</url>
                    <url>img2.jpg</url>
                </image_urls>
            </product>
            ...
        </products>
    """

    def __init__(self, file, **kwargs):
        super().__init__(**kwargs)
        self.file = file
        self.root = ET.Element('products')
        self.root.set('version', '1.0')
        self.root.set('encoding', 'UTF-8')

    def export_item(self, item):
        """Добавляет товар в XML структуру."""
        product_elem = ET.SubElement(self.root, 'product')

        itemdict = dict(self._get_serialized_fields(item))

        for key, value in itemdict.items():
            self._add_element(product_elem, key, value)

    def _add_element(self, parent: ET.Element, key: str, value: Any):
        """
        Рекурсивно добавляет элемент в XML.

        Обрабатывает:
        - Скалярные значения (строки, числа, bool)
        - Списки (создаёт вложенные элементы)
        - Словари (создаёт вложенную структуру)
        - None (игнорирует)

        Args:
            parent: Родительский XML элемент
            key: Ключ (имя элемента)
            value: Значение
        """
        if value is None:
            return

        # Заменяем некорректные символы в названии элемента
        elem_name = self._sanitize_elem_name(key)

        if isinstance(value, (list, tuple)):
            # Для списков создаём контейнер с вложенными элементами
            if value:
                container = ET.SubElement(parent, elem_name)
                for item in value:
                    if isinstance(item, dict):
                        item_elem = ET.SubElement(container, 'item')
                        for k, v in item.items():
                            self._add_element(item_elem, k, v)
                    else:
                        item_elem = ET.SubElement(container, 'item')
                        item_elem.text = str(item)
        elif isinstance(value, dict):
            # Для словарей создаём вложенную структуру
            dict_elem = ET.SubElement(parent, elem_name)
            for k, v in value.items():
                self._add_element(dict_elem, k, v)
        else:
            # Для скалярных значений просто устанавливаем текст
            elem = ET.SubElement(parent, elem_name)
            if isinstance(value, bool):
                elem.text = 'true' if value else 'false'
            else:
                elem.text = str(value)

    def _sanitize_elem_name(self, name: str) -> str:
        """
        Преобразует название в валидный XML элемент.

        XML требует:
        - Начинаться с буквы или подчёркивания
        - Содержать только буквы, цифры, точки, дефисы и подчёркивания

        Args:
            name: Исходное название

        Returns:
            Валидное XML имя элемента
        """
        # Заменяем недопустимые символы на подчёркивание
        sanitized = ''
        for i, char in enumerate(name.lower()):
            if char.isalnum() or char in ('_', '-', '.'):
                sanitized += char
            else:
                sanitized += '_'

        # Убеждаемся что элемент начинается с буквы или подчёркивания
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == '_'):
            sanitized = '_' + sanitized

        return sanitized or 'item'

    def finish_exporting(self):
        """Записывает XML в файл с красивым форматированием."""
        # Форматируем XML
        rough_string = ET.tostring(self.root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent='  ')

        # Удаляем первую строку (XML declaration автоматически добавлена minidom)
        # и пустые строки
        lines = pretty_xml.split('\n')[1:]
        pretty_xml = '\n'.join(line for line in lines if line.strip())

        self.file.write(pretty_xml)


# Экспортеры для использования по умолчанию
__all__ = [
    'JsonLinesItemExporter',
    'CsvItemExporter',
    'XmlItemExporter',
]
