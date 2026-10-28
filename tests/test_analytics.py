"""Unit tests for the Analytics Data Access Layer."""
import unittest
import pandas as pd
from analytics.queries import AnalyticsEngine, get_analytics_engine


class TestAnalyticsEngine(unittest.TestCase):
    """Test suite covering local analytics computations and dynamic filtering."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = get_analytics_engine()

    def test_load_local_data_returns_records(self) -> None:
        """Verify that load_local_data loads the processed Parquet dataset."""
        df = self.engine.load_local_data()
        self.assertFalse(df.empty)
        self.assertIn("total_amount", df.columns)
        self.assertIn("category", df.columns)
        self.assertIn("region", df.columns)

    def test_kpi_summary_values(self) -> None:
        """Verify that KPIs calculate expected sums and averages."""
        kpis = self.engine.get_kpi_summary()
        self.assertGreater(kpis["total_revenue"], 100000.0)
        self.assertGreater(kpis["total_orders"], 400)
        self.assertGreater(kpis["total_quantity"], 1000)
        self.assertGreater(kpis["average_order_value"], 0.0)

    def test_monthly_revenue_trend(self) -> None:
        """Verify monthly aggregation structure and sorting."""
        monthly_df = self.engine.get_monthly_revenue_trend()
        self.assertFalse(monthly_df.empty)
        self.assertIn("order_year_month", monthly_df.columns)
        self.assertIn("monthly_revenue", monthly_df.columns)
        self.assertIn("monthly_orders", monthly_df.columns)

    def test_category_revenue_and_share(self) -> None:
        """Verify category breakdown and that shares sum to ~100%."""
        cat_df = self.engine.get_category_revenue()
        self.assertFalse(cat_df.empty)
        self.assertIn("category", cat_df.columns)
        self.assertIn("category_revenue", cat_df.columns)
        self.assertIn("share_percent", cat_df.columns)
        total_share = cat_df["share_percent"].sum()
        self.assertAlmostEqual(total_share, 100.0, delta=0.5)

    def test_top_products_limit(self) -> None:
        """Verify top products limit and sorting."""
        top_df = self.engine.get_top_products(limit=5)
        self.assertEqual(len(top_df), 5)
        self.assertIn("product_name", top_df.columns)
        self.assertIn("product_revenue", top_df.columns)
        # Verify descending order
        revenues = top_df["product_revenue"].tolist()
        self.assertEqual(revenues, sorted(revenues, reverse=True))

    def test_region_revenue(self) -> None:
        """Verify regional aggregation."""
        reg_df = self.engine.get_region_revenue()
        self.assertFalse(reg_df.empty)
        self.assertIn("region", reg_df.columns)
        self.assertIn("regional_revenue", reg_df.columns)

    def test_day_of_week_trends(self) -> None:
        """Verify weekday ordering."""
        day_df = self.engine.get_day_of_week_trends()
        self.assertFalse(day_df.empty)
        self.assertIn("order_day_name", day_df.columns)
        self.assertIn("day_revenue", day_df.columns)

    def test_filtering_by_category(self) -> None:
        """Verify that passing category filter restricts the results accurately."""
        all_kpis = self.engine.get_kpi_summary()
        elec_kpis = self.engine.get_kpi_summary(category="Electronics")
        self.assertGreater(all_kpis["total_revenue"], elec_kpis["total_revenue"])
        self.assertGreater(elec_kpis["total_revenue"], 0.0)

    def test_filtering_by_region(self) -> None:
        """Verify that passing region filter restricts the results accurately."""
        all_kpis = self.engine.get_kpi_summary()
        na_kpis = self.engine.get_kpi_summary(region="North America")
        self.assertGreater(all_kpis["total_revenue"], na_kpis["total_revenue"])
        self.assertGreater(na_kpis["total_revenue"], 0.0)

    def test_empty_filter_graceful_handling(self) -> None:
        """Verify that an impossible date range returns 0 KPIs without exceptions."""
        kpis = self.engine.get_kpi_summary(start_date="2099-01-01", end_date="2099-01-02")
        self.assertEqual(kpis["total_revenue"], 0.0)
        self.assertEqual(kpis["total_orders"], 0)
        self.assertEqual(kpis["average_order_value"], 0.0)


if __name__ == "__main__":
    unittest.main()
