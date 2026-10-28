"""Unit tests for the ETL Transformation and Quality Validation module."""
import unittest
import pandas as pd
from etl.transform import transform_sales_data, normalize_category_name


class TestTransform(unittest.TestCase):
    """Test suite covering data cleaning, deduplication, and quarantine routing."""

    def test_category_normalization(self) -> None:
        """Verify that inconsistent category casings and spaces are canonicalized."""
        self.assertEqual(normalize_category_name("  electronics  "), "Electronics")
        self.assertEqual(normalize_category_name("CLOTHING"), "Clothing")
        self.assertEqual(normalize_category_name("home kitchen"), "Home & Kitchen")
        self.assertEqual(normalize_category_name("sports & fitness"), "Fitness")
        self.assertEqual(normalize_category_name("books"), "Books")

    def test_missing_mandatory_fields_quarantined(self) -> None:
        """Verify records with missing required fields are routed to rejected partition."""
        data = {
            "order_id": ["ORD-1", "ORD-2", "ORD-3"],
            "order_date": ["2026-10-01 10:00:00", "2026-10-01 10:00:00", "2026-10-01 10:00:00"],
            "product_id": ["P1", "P2", "P3"],
            "product_name": ["Prod 1", "Prod 2", "Prod 3"],
            "category": ["Electronics", "", "Books"],  # ORD-2 has empty category
            "quantity": ["1", "2", "3"],
            "unit_price": ["10.0", "20.0", ""],  # ORD-3 has empty unit_price
            "region": ["North America", "Europe", "Asia-Pacific"],
            "customer_id": ["", "CUST-2", "CUST-3"],  # ORD-1 has empty customer_id
        }
        df = pd.DataFrame(data)
        result = transform_sales_data(df)

        self.assertEqual(result.metrics.clean_count, 0)
        self.assertEqual(result.metrics.rejected_count, 3)
        self.assertEqual(result.metrics.missing_values_count, 3)
        self.assertEqual(len(result.rejected_df), 3)

    def test_duplicate_order_id_quarantined(self) -> None:
        """Verify that duplicate order IDs are detected and subsequent rows quarantined."""
        data = {
            "order_id": ["ORD-100", "ORD-100"],  # Duplicate
            "order_date": ["2026-10-01 10:00:00", "2026-10-01 10:00:00"],
            "product_id": ["P1", "P1"],
            "product_name": ["Prod 1", "Prod 1"],
            "category": ["Electronics", "Electronics"],
            "quantity": ["1", "1"],
            "unit_price": ["50.0", "50.0"],
            "region": ["North America", "North America"],
            "customer_id": ["C1", "C1"],
        }
        df = pd.DataFrame(data)
        result = transform_sales_data(df)

        self.assertEqual(result.metrics.clean_count, 1)
        self.assertEqual(result.metrics.rejected_count, 1)
        self.assertEqual(result.metrics.duplicates_count, 1)
        self.assertIn("DUPLICATE_ORDER_ID", result.rejected_df.iloc[0]["rejection_reason"])

    def test_invalid_quantity_quarantined(self) -> None:
        """Verify that negative, zero, and non-numeric quantities are quarantined."""
        data = {
            "order_id": ["ORD-10", "ORD-11", "ORD-12", "ORD-13"],
            "order_date": ["2026-10-01 10:00:00"] * 4,
            "product_id": ["P1"] * 4,
            "product_name": ["Prod"] * 4,
            "category": ["Electronics"] * 4,
            "quantity": ["0", "-5", "not_a_num", "3"],
            "unit_price": ["100.0"] * 4,
            "region": ["Europe"] * 4,
            "customer_id": ["C1"] * 4,
        }
        df = pd.DataFrame(data)
        result = transform_sales_data(df)

        self.assertEqual(result.metrics.clean_count, 1)
        self.assertEqual(result.metrics.rejected_count, 3)
        self.assertEqual(result.metrics.invalid_quantities_count, 3)

    def test_invalid_prices_quarantined(self) -> None:
        """Verify that zero, negative, or non-numeric prices are quarantined."""
        data = {
            "order_id": ["ORD-20", "ORD-21", "ORD-22", "ORD-23"],
            "order_date": ["2026-10-01 10:00:00"] * 4,
            "product_id": ["P1"] * 4,
            "product_name": ["Prod"] * 4,
            "category": ["Books"] * 4,
            "quantity": ["2"] * 4,
            "unit_price": ["0.0", "-15.50", "free", "25.00"],
            "region": ["Middle East"] * 4,
            "customer_id": ["C1"] * 4,
        }
        df = pd.DataFrame(data)
        result = transform_sales_data(df)

        self.assertEqual(result.metrics.clean_count, 1)
        self.assertEqual(result.metrics.rejected_count, 3)
        self.assertEqual(result.metrics.invalid_prices_count, 3)

    def test_malformed_dates_quarantined(self) -> None:
        """Verify that unparseable date strings are rejected."""
        data = {
            "order_id": ["ORD-30", "ORD-31"],
            "order_date": ["99/99/2026", "2026-10-15 14:00:00"],
            "product_id": ["P1", "P1"],
            "product_name": ["Prod", "Prod"],
            "category": ["Fitness", "Fitness"],
            "quantity": ["1", "1"],
            "unit_price": ["20.0", "20.0"],
            "region": ["Europe", "Europe"],
            "customer_id": ["C1", "C1"],
        }
        df = pd.DataFrame(data)
        result = transform_sales_data(df)

        self.assertEqual(result.metrics.clean_count, 1)
        self.assertEqual(result.metrics.rejected_count, 1)
        self.assertEqual(result.metrics.invalid_dates_count, 1)
        self.assertIn("MALFORMED_DATE", result.rejected_df.iloc[0]["rejection_reason"])

    def test_revenue_and_feature_engineering(self) -> None:
        """Verify that clean rows calculate total_amount and date components correctly."""
        data = {
            "order_id": ["ORD-40"],
            "order_date": ["2026-08-15 10:30:00"],
            "product_id": ["PROD-101"],
            "product_name": ["Headphones"],
            "category": ["electronics"],
            "quantity": ["3"],
            "unit_price": ["99.50"],
            "region": ["North America"],
            "customer_id": ["CUST-10"],
        }
        df = pd.DataFrame(data)
        result = transform_sales_data(df)

        self.assertEqual(result.metrics.clean_count, 1)
        clean_row = result.clean_df.iloc[0]
        # Total amount = 3 * 99.50 = 298.50
        self.assertAlmostEqual(clean_row["total_amount"], 298.50)
        self.assertEqual(clean_row["order_year"], 2026)
        self.assertEqual(clean_row["order_month"], 8)
        self.assertEqual(clean_row["order_day"], 15)
        self.assertEqual(clean_row["order_year_month"], "2026-08")
        self.assertEqual(clean_row["category"], "Electronics")

    def test_empty_dataframe(self) -> None:
        """Verify that transforming an empty DataFrame returns empty partitions gracefully."""
        df = pd.DataFrame()
        result = transform_sales_data(df)
        self.assertEqual(result.metrics.clean_count, 0)
        self.assertEqual(result.metrics.rejected_count, 0)
        self.assertTrue(result.clean_df.empty)


if __name__ == "__main__":
    unittest.main()
