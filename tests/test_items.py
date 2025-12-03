import unittest
from datetime import datetime
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'alkoteka_parser', 'alkoteka_parser'))

from items import (
    parse_price,
    calculate_discount,
    clean_title,
    extract_number,
    extract_float,
    is_valid_email,
    normalize_bool,
)


class TestParsePrice(unittest.TestCase):
    def test_parse_price_simple_float(self):
        self.assertEqual(parse_price("450.00"), 450.0)

    def test_parse_price_european_format(self):
        self.assertEqual(parse_price("450,00"), 450.0)

    def test_parse_price_with_currency(self):
        self.assertEqual(parse_price("450 руб."), 450.0)
        self.assertEqual(parse_price("$450.00"), 450.0)

    def test_parse_price_with_spaces(self):
        self.assertEqual(parse_price("  450.00  "), 450.0)

    def test_parse_price_integer(self):
        self.assertEqual(parse_price("450"), 450.0)

    def test_parse_price_none(self):
        self.assertIsNone(parse_price(None))

    def test_parse_price_empty_string(self):
        self.assertIsNone(parse_price(""))

    def test_parse_price_invalid(self):
        self.assertIsNone(parse_price("abc"))

    def test_parse_price_complex(self):
        self.assertEqual(parse_price("Цена: 1 234,50 РУБ"), 1234.50)


class TestCalculateDiscount(unittest.TestCase):
    def test_calculate_discount_50_percent(self):
        self.assertEqual(calculate_discount(1000.0, 500.0), 50)

    def test_calculate_discount_25_percent(self):
        self.assertEqual(calculate_discount(1000.0, 750.0), 25)

    def test_calculate_discount_no_discount(self):
        self.assertEqual(calculate_discount(1000.0, 1000.0), 0)

    def test_calculate_discount_none_values(self):
        self.assertIsNone(calculate_discount(None, 500.0))
        self.assertIsNone(calculate_discount(1000.0, None))
        self.assertIsNone(calculate_discount(None, None))

    def test_calculate_discount_zero_original(self):
        self.assertIsNone(calculate_discount(0, 500.0))

    def test_calculate_discount_negative_prices(self):
        self.assertIsNone(calculate_discount(-1000.0, -500.0))

    def test_calculate_discount_rounding(self):
        self.assertEqual(calculate_discount(1000.0, 333.33), 66)


class TestCleanTitle(unittest.TestCase):
    def test_clean_title_with_spaces(self):
        result = clean_title("  Водка   'Русский стандарт'  ")
        self.assertEqual(result, "Водка 'Русский стандарт'")

    def test_clean_title_multiple_spaces(self):
        result = clean_title("Vodka    Absolut    Vodka")
        self.assertEqual(result, "Vodka Absolut Vodka")

    def test_clean_title_tabs_and_newlines(self):
        result = clean_title("Title\t\nWith\nNewlines")
        self.assertEqual(result, "Title With Newlines")

    def test_clean_title_none(self):
        self.assertEqual(clean_title(None), "")

    def test_clean_title_empty_string(self):
        self.assertEqual(clean_title(""), "")

    def test_clean_title_already_clean(self):
        result = clean_title("Водка Русский стандарт")
        self.assertEqual(result, "Водка Русский стандарт")


class TestExtractNumber(unittest.TestCase):
    def test_extract_number_from_volume(self):
        self.assertEqual(extract_number("750ml"), 750)

    def test_extract_number_from_availability(self):
        self.assertEqual(extract_number("Availability: 5 items"), 5)

    def test_extract_number_none(self):
        self.assertIsNone(extract_number(None))

    def test_extract_number_empty(self):
        self.assertIsNone(extract_number(""))

    def test_extract_number_no_digits(self):
        self.assertIsNone(extract_number("no digits here"))

    def test_extract_number_multiple_numbers(self):
        self.assertEqual(extract_number("Year 2020 Volume 750"), 2020)

    def test_extract_number_from_price(self):
        self.assertEqual(extract_number("Цена: 450 руб"), 450)


class TestExtractFloat(unittest.TestCase):
    def test_extract_float_from_rating(self):
        self.assertEqual(extract_float("Rating: 4.5 stars"), 4.5)

    def test_extract_float_integer(self):
        self.assertEqual(extract_float("Rating: 5 stars"), 5.0)

    def test_extract_float_none(self):
        self.assertIsNone(extract_float(None))

    def test_extract_float_empty(self):
        self.assertIsNone(extract_float(""))

    def test_extract_float_no_digits(self):
        self.assertIsNone(extract_float("no numbers here"))

    def test_extract_float_multiple_floats(self):
        self.assertEqual(extract_float("Price 450.50 Rating 4.5"), 450.5)


class TestIsValidEmail(unittest.TestCase):
    def test_valid_email_simple(self):
        self.assertTrue(is_valid_email("user@example.com"))

    def test_valid_email_with_dots(self):
        self.assertTrue(is_valid_email("user.name@example.com"))

    def test_valid_email_with_numbers(self):
        self.assertTrue(is_valid_email("user123@example123.com"))

    def test_valid_email_with_hyphen(self):
        self.assertTrue(is_valid_email("user@example-domain.com"))

    def test_invalid_email_no_at(self):
        self.assertFalse(is_valid_email("userexample.com"))

    def test_invalid_email_no_domain(self):
        self.assertFalse(is_valid_email("user@"))

    def test_invalid_email_no_extension(self):
        self.assertFalse(is_valid_email("user@example"))

    def test_invalid_email_empty(self):
        self.assertFalse(is_valid_email(""))

    def test_invalid_email_none(self):
        self.assertFalse(is_valid_email(None))

    def test_invalid_email_special_chars(self):
        self.assertFalse(is_valid_email("user@#@example.com"))


class TestNormalizeBool(unittest.TestCase):
    def test_normalize_bool_true_string(self):
        self.assertTrue(normalize_bool("true"))

    def test_normalize_bool_yes_string(self):
        self.assertTrue(normalize_bool("yes"))

    def test_normalize_bool_one_string(self):
        self.assertTrue(normalize_bool("1"))

    def test_normalize_bool_available_string(self):
        self.assertTrue(normalize_bool("available"))

    def test_normalize_bool_in_stock_string(self):
        self.assertTrue(normalize_bool("in stock"))

    def test_normalize_bool_false_string(self):
        self.assertFalse(normalize_bool("false"))

    def test_normalize_bool_no_string(self):
        self.assertFalse(normalize_bool("no"))

    def test_normalize_bool_zero_string(self):
        self.assertFalse(normalize_bool("0"))

    def test_normalize_bool_integer_one(self):
        self.assertTrue(normalize_bool(1))

    def test_normalize_bool_integer_zero(self):
        self.assertFalse(normalize_bool(0))

    def test_normalize_bool_bool_true(self):
        self.assertTrue(normalize_bool(True))

    def test_normalize_bool_bool_false(self):
        self.assertFalse(normalize_bool(False))

    def test_normalize_bool_case_insensitive(self):
        self.assertTrue(normalize_bool("TRUE"))
        self.assertTrue(normalize_bool("TrUe"))
        self.assertTrue(normalize_bool("YES"))

    def test_normalize_bool_with_spaces(self):
        self.assertTrue(normalize_bool("  true  "))
        self.assertFalse(normalize_bool("  false  "))


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestParsePrice))
    suite.addTests(loader.loadTestsFromTestCase(TestCalculateDiscount))
    suite.addTests(loader.loadTestsFromTestCase(TestCleanTitle))
    suite.addTests(loader.loadTestsFromTestCase(TestExtractNumber))
    suite.addTests(loader.loadTestsFromTestCase(TestExtractFloat))
    suite.addTests(loader.loadTestsFromTestCase(TestIsValidEmail))
    suite.addTests(loader.loadTestsFromTestCase(TestNormalizeBool))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    exit(0 if result.wasSuccessful() else 1)
