import io
from datetime import date

from django.test import SimpleTestCase

from archive.management.importers.lancaster import LancasterImporter


class LancasterImporterDateTests(SimpleTestCase):
    def setUp(self):
        self.importer = LancasterImporter(
            dry_run=True,
            include_names=False,
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            identifier_prefix="L",
            identifier_width=8,
            identifier_system="https://example.test/identifier-system/lancaster",
            collection_short_name="Lancaster",
            collection_full_name="Lancaster",
        )

    def test_format_identifier_zero_padding(self):
        self.assertEqual(self.importer._format_identifier("4001"), "L00004001")

    def test_parse_full_date_with_two_digit_year(self):
        parsed = self.importer._parse_full_date("12/31/63")
        self.assertEqual(parsed, date(1963, 12, 31))

    def test_parse_full_date_with_four_digit_year(self):
        parsed = self.importer._parse_full_date("1/2/1987")
        self.assertEqual(parsed, date(1987, 1, 2))

    def test_parse_encounter_full_date(self):
        parsed = self.importer._parse_encounter_token("3/5/64", date(1960, 1, 1))
        self.assertEqual(parsed, (date(1964, 3, 5), "day", False, "3/5/64"))

    def test_parse_encounter_month_year_midpoint(self):
        parsed = self.importer._parse_encounter_token("4/87", date(1960, 1, 1))
        self.assertEqual(parsed, (date(1987, 4, 15), "month", True, "4/87"))

    def test_parse_encounter_year_only_midpoint(self):
        parsed = self.importer._parse_encounter_token("1979", date(1960, 1, 1))
        self.assertEqual(parsed, (date(1979, 7, 2), "year", True, "1979"))

    def test_parse_encounter_unknown_day(self):
        parsed = self.importer._parse_encounter_token("8/?/65", date(1960, 1, 1))
        self.assertEqual(parsed, (date(1965, 8, 16), "month", True, "8/?/65"))

    def test_parse_encounter_unknown_month_day(self):
        parsed = self.importer._parse_encounter_token("?/?/1961", date(1960, 1, 1))
        self.assertEqual(parsed, (date(1961, 7, 2), "year", True, "?/?/1961"))

    def test_parse_encounter_age_years(self):
        parsed = self.importer._parse_encounter_token("age: 10 yrs", date(2000, 1, 1))
        self.assertEqual(parsed, (date(2010, 7, 2), "year", True, "age: 10 yrs"))

    def test_parse_encounter_age_months(self):
        parsed = self.importer._parse_encounter_token("age: 3 mos.", date(2000, 1, 1))
        self.assertEqual(parsed, (date(2000, 4, 15), "month", True, "age: 3 mos."))

    def test_parse_encounter_age_days(self):
        parsed = self.importer._parse_encounter_token("age: 5 days", date(2000, 1, 1))
        self.assertEqual(parsed, (date(2000, 1, 6), "day", True, "age: 5 days"))

    def test_parse_encounter_invalid_token(self):
        parsed = self.importer._parse_encounter_token("unknown", date(1960, 1, 1))
        self.assertIsNone(parsed)
