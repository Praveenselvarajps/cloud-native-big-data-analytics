"""Unit tests for Phase 1 sample dataset generation and configuration.

Supports execution with both pytest and Python standard library unittest:
    pytest tests/
    python -m unittest discover tests/
"""
import unittest
import csv
import tempfile
from pathlib import Path
from scripts.generate_sample_data import (
    generate_dataset,
    save_to_csv,
    PRODUCTS_CATALOG,
    REGIONS,
)
from config.settings import settings


class TestDataGeneration(unittest.TestCase):
    """Test suite for sample data generation and configuration."""

    def test_settings_load(self) -> None:
        """Verify that configuration settings load with sensible defaults."""
        self.assertIn(settings.app_env, ["development", "production", "test"])
        self.assertTrue(settings.base_dir.exists())
        self.assertTrue(settings.s3_raw_prefix.endswith("/"))
        self.assertTrue(settings.s3_processed_prefix.endswith("/"))

    def test_generate_dataset_structure(self) -> None:
        """Verify that generate_dataset generates the correct schema and count."""
        valid_count = 50
        records, summary = generate_dataset(valid_count=valid_count)

        expected_columns = {
            "order_id",
            "order_date",
            "product_id",
            "product_name",
            "category",
            "quantity",
            "unit_price",
            "region",
            "customer_id",
        }

        self.assertGreater(len(records), valid_count)
        self.assertGreater(sum(summary.values()), 0)

        # Verify that all expected columns are present in every generated record
        for record in records:
            self.assertTrue(expected_columns.issubset(record.keys()))

    def test_save_to_csv_creates_valid_file(self) -> None:
        """Verify that saving records creates a readable CSV file with headers."""
        sample_records, _ = generate_dataset(valid_count=10)
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "test_sales.csv"

            save_to_csv(sample_records, output_file)

            self.assertTrue(output_file.exists())
            self.assertGreater(output_file.stat().st_size, 0)

            # Verify CSV headers
            with open(output_file, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                self.assertIn("order_id", header)
                self.assertIn("unit_price", header)
                self.assertIn("category", header)


if __name__ == "__main__":
    unittest.main()
