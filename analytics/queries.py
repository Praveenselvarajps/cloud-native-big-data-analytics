"""Data Access Layer for Analytical Queries (Athena & Local Engine).

Provides a unified interface for analytical queries:
1. Production Mode: Executes SQL queries on Amazon Athena using Boto3,
   polls query execution states (QUEUED, RUNNING, SUCCEEDED, FAILED),
   and streams tabular results into Pandas DataFrames.
2. Local Development Mode: Reads the processed Parquet dataset directly
   and executes equivalent Pandas analytics with zero external cloud dependencies.
"""
from datetime import datetime, date
import json
import logging
from pathlib import Path
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd
from config.settings import settings

logger = logging.getLogger(__name__)


class AnalyticsError(Exception):
    """Base exception for analytics query errors."""
    pass


class AnalyticsEngine:
    """Unified Analytics Data Access Layer supporting both Athena and Local Parquet."""

    def __init__(self, mode: Optional[str] = None):
        self.mode = mode or settings.app_env
        self.is_production = (self.mode == "production")
        self.athena_client = None
        self._local_df: Optional[pd.DataFrame] = None

        if self.is_production:
            try:
                import boto3
                if settings.aws_access_key_id and settings.aws_secret_access_key:
                    self.athena_client = boto3.client(
                        "athena",
                        region_name=settings.aws_region,
                        aws_access_key_id=settings.aws_access_key_id,
                        aws_secret_access_key=settings.aws_secret_access_key,
                    )
                else:
                    self.athena_client = boto3.client("athena", region_name=settings.aws_region)
                logger.info("Initialized Amazon Athena Analytics Engine (Cloud Mode).")
            except Exception as exc:
                logger.warning(
                    f"Could not initialize Athena client ({exc}). Falling back to Local Engine."
                )
                self.is_production = False

    def load_local_data(self) -> pd.DataFrame:
        """Load clean processed records from local Parquet file."""
        parquet_path = settings.processed_data_dir / "orders_clean.parquet"
        if not parquet_path.exists():
            # Fallback to CSV if Parquet not yet generated
            csv_path = settings.processed_data_dir / "orders_clean.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                df["order_date"] = pd.to_datetime(df["order_date"])
                return df
            return pd.DataFrame()

        df = pd.read_parquet(parquet_path)
        if not pd.api.types.is_datetime64_any_dtype(df["order_date"]):
            df["order_date"] = pd.to_datetime(df["order_date"])
        return df

    def execute_athena_sql(self, query: str, timeout_seconds: int = 45) -> pd.DataFrame:
        """Execute a SQL statement on Amazon Athena and return results as DataFrame."""
        if not self.athena_client:
            raise AnalyticsError("Athena client is not initialized.")

        try:
            logger.info(f"Executing Athena SQL Query on database: {settings.athena_database}")
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": settings.athena_database},
                ResultConfiguration={"OutputLocation": settings.athena_output_location},
            )
            query_execution_id = response["QueryExecutionId"]

            # Poll for query completion with exponential backoff
            start_time = time.time()
            backoff = 0.5
            while time.time() - start_time < timeout_seconds:
                status_resp = self.athena_client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                state = status_resp["QueryExecution"]["Status"]["State"]

                if state == "SUCCEEDED":
                    logger.info(f"Athena Query {query_execution_id} succeeded.")
                    return self._fetch_athena_results(query_execution_id)
                elif state in ["FAILED", "CANCELLED"]:
                    reason = status_resp["QueryExecution"]["Status"].get(
                        "StateChangeReason", "Unknown error"
                    )
                    raise AnalyticsError(f"Athena query {state}: {reason}")

                time.sleep(backoff)
                backoff = min(backoff * 1.5, 3.0)

            raise AnalyticsError(f"Athena query timed out after {timeout_seconds} seconds.")
        except Exception as exc:
            logger.error(f"Athena execution error: {exc}")
            raise AnalyticsError(f"Athena Query Failed: {str(exc)}") from exc

    def _fetch_athena_results(self, query_execution_id: str) -> pd.DataFrame:
        """Fetch and convert Athena tabular result set into a pandas DataFrame."""
        result_resp = self.athena_client.get_query_results(QueryExecutionId=query_execution_id)
        rows = result_resp["ResultSet"]["Rows"]
        if not rows:
            return pd.DataFrame()

        # First row is headers
        headers = [col.get("VarCharValue", "") for col in rows[0]["Data"]]
        records = []
        for r in rows[1:]:
            records.append([col.get("VarCharValue", None) for col in r["Data"]])

        df = pd.DataFrame(records, columns=headers)
        return df

    # --------------------------------------------------------------------------
    # HIGH-LEVEL ANALYTICS METHODS (WITH DYNAMIC FILTERING)
    # --------------------------------------------------------------------------

    def _filter_dataframe(
        self,
        df: pd.DataFrame,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        category: Optional[str] = None,
        region: Optional[str] = None,
    ) -> pd.DataFrame:
        """Apply user filters to DataFrame safely."""
        if df.empty:
            return df

        filtered = df.copy()

        if start_date:
            ts_start = pd.to_datetime(start_date)
            filtered = filtered[filtered["order_date"] >= ts_start]

        if end_date:
            ts_end = pd.to_datetime(end_date)
            # Extend to end of day if only date is passed
            if isinstance(end_date, (date, str)) and " " not in str(end_date):
                ts_end = ts_end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            filtered = filtered[filtered["order_date"] <= ts_end]

        if category and category.lower() != "all":
            filtered = filtered[filtered["category"].str.lower() == category.lower()]

        if region and region.lower() != "all":
            filtered = filtered[filtered["region"].str.lower() == region.lower()]

        return filtered

    def get_kpi_summary(
        self,
        start_date=None,
        end_date=None,
        category=None,
        region=None,
    ) -> Dict[str, Any]:
        """Calculate executive KPIs: Total Revenue, Orders, Quantity, and AOV."""
        df = self.load_local_data()
        filtered = self._filter_dataframe(df, start_date, end_date, category, region)

        if filtered.empty:
            return {
                "total_revenue": 0.0,
                "total_orders": 0,
                "total_quantity": 0,
                "average_order_value": 0.0,
            }

        total_rev = float(filtered["total_amount"].sum())
        total_orders = int(filtered["order_id"].nunique())
        total_qty = int(filtered["quantity"].sum())
        aov = round(total_rev / total_orders, 2) if total_orders > 0 else 0.0

        return {
            "total_revenue": round(total_rev, 2),
            "total_orders": total_orders,
            "total_quantity": total_qty,
            "average_order_value": aov,
        }

    def get_monthly_revenue_trend(
        self,
        start_date=None,
        end_date=None,
        category=None,
        region=None,
    ) -> pd.DataFrame:
        """Aggregate monthly order volume and revenue."""
        df = self.load_local_data()
        filtered = self._filter_dataframe(df, start_date, end_date, category, region)

        if filtered.empty:
            return pd.DataFrame(columns=["order_year_month", "monthly_revenue", "monthly_orders"])

        monthly = (
            filtered.groupby("order_year_month")
            .agg(
                monthly_revenue=("total_amount", "sum"),
                monthly_orders=("order_id", "nunique"),
                units_sold=("quantity", "sum"),
            )
            .reset_index()
            .sort_values("order_year_month")
        )
        monthly["monthly_revenue"] = monthly["monthly_revenue"].round(2)
        return monthly

    def get_category_revenue(
        self,
        start_date=None,
        end_date=None,
        category=None,
        region=None,
    ) -> pd.DataFrame:
        """Aggregate revenue and percentage share by category."""
        df = self.load_local_data()
        filtered = self._filter_dataframe(df, start_date, end_date, category, region)

        if filtered.empty:
            return pd.DataFrame(columns=["category", "category_revenue", "total_orders"])

        cat_df = (
            filtered.groupby("category")
            .agg(
                category_revenue=("total_amount", "sum"),
                total_orders=("order_id", "nunique"),
                units_sold=("quantity", "sum"),
            )
            .reset_index()
            .sort_values("category_revenue", ascending=False)
        )
        cat_df["category_revenue"] = cat_df["category_revenue"].round(2)
        total = cat_df["category_revenue"].sum()
        cat_df["share_percent"] = (
            (cat_df["category_revenue"] / total * 100.0).round(2) if total > 0 else 0.0
        )
        return cat_df

    def get_top_products(
        self,
        limit: int = 5,
        start_date=None,
        end_date=None,
        category=None,
        region=None,
    ) -> pd.DataFrame:
        """Retrieve top products by total sales revenue."""
        df = self.load_local_data()
        filtered = self._filter_dataframe(df, start_date, end_date, category, region)

        if filtered.empty:
            return pd.DataFrame(columns=["product_name", "category", "product_revenue", "units_sold"])

        prod_df = (
            filtered.groupby(["product_id", "product_name", "category"])
            .agg(
                product_revenue=("total_amount", "sum"),
                units_sold=("quantity", "sum"),
                avg_price=("unit_price", "mean"),
            )
            .reset_index()
            .sort_values("product_revenue", ascending=False)
            .head(limit)
        )
        prod_df["product_revenue"] = prod_df["product_revenue"].round(2)
        prod_df["avg_price"] = prod_df["avg_price"].round(2)
        return prod_df

    def get_region_revenue(
        self,
        start_date=None,
        end_date=None,
        category=None,
        region=None,
    ) -> pd.DataFrame:
        """Aggregate revenue by geographic region."""
        df = self.load_local_data()
        filtered = self._filter_dataframe(df, start_date, end_date, category, region)

        if filtered.empty:
            return pd.DataFrame(columns=["region", "regional_revenue", "orders_count"])

        reg_df = (
            filtered.groupby("region")
            .agg(
                regional_revenue=("total_amount", "sum"),
                orders_count=("order_id", "nunique"),
                units_sold=("quantity", "sum"),
            )
            .reset_index()
            .sort_values("regional_revenue", ascending=False)
        )
        reg_df["regional_revenue"] = reg_df["regional_revenue"].round(2)
        total = reg_df["regional_revenue"].sum()
        reg_df["share_percent"] = (
            (reg_df["regional_revenue"] / total * 100.0).round(2) if total > 0 else 0.0
        )
        return reg_df

    def get_day_of_week_trends(
        self,
        start_date=None,
        end_date=None,
        category=None,
        region=None,
    ) -> pd.DataFrame:
        """Aggregate orders and revenue by day of week."""
        df = self.load_local_data()
        filtered = self._filter_dataframe(df, start_date, end_date, category, region)

        if filtered.empty:
            return pd.DataFrame(columns=["order_day_name", "day_revenue", "orders_count"])

        weekday_order = [
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ]
        day_df = (
            filtered.groupby("order_day_name")
            .agg(
                day_revenue=("total_amount", "sum"),
                orders_count=("order_id", "nunique"),
            )
            .reset_index()
        )
        day_df["day_revenue"] = day_df["day_revenue"].round(2)
        day_df["order_day_name"] = pd.Categorical(
            day_df["order_day_name"], categories=weekday_order, ordered=True
        )
        return day_df.sort_values("order_day_name")

    def get_distinct_categories(self) -> List[str]:
        """Fetch unique canonical categories."""
        df = self.load_local_data()
        if df.empty or "category" not in df.columns:
            return []
        return sorted([str(c) for c in df["category"].dropna().unique()])

    def get_distinct_regions(self) -> List[str]:
        """Fetch unique regions."""
        df = self.load_local_data()
        if df.empty or "region" not in df.columns:
            return []
        return sorted([str(r) for r in df["region"].dropna().unique()])

    def get_date_bounds(self) -> Tuple[datetime, datetime]:
        """Fetch min and max dates available in dataset."""
        df = self.load_local_data()
        if df.empty or "order_date" not in df.columns:
            now = datetime.utcnow()
            return now, now
        return df["order_date"].min().to_pydatetime(), df["order_date"].max().to_pydatetime()

    def get_etl_monitoring_stats(self) -> Dict[str, Any]:
        """Retrieve audit statistics from latest ETL execution."""
        summary_file = settings.processed_data_dir / "latest_etl_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        # Fallback inspection of files directly
        clean_df = self.load_local_data()
        rejected_file = settings.rejected_data_dir / "orders_rejected.csv"
        rejected_count = 0
        if rejected_file.exists():
            try:
                rej_df = pd.read_csv(rejected_file)
                rejected_count = len(rej_df)
            except Exception:
                pass

        return {
            "status": "SUCCESS" if not clean_df.empty else "UNKNOWN",
            "start_time": "N/A",
            "end_time": "N/A",
            "duration_seconds": 0.0,
            "input_records": len(clean_df) + rejected_count,
            "clean_records": len(clean_df),
            "rejected_records": rejected_count,
            "total_revenue": float(clean_df["total_amount"].sum()) if not clean_df.empty else 0.0,
            "rejection_breakdown": {},
        }


def get_analytics_engine() -> AnalyticsEngine:
    """Factory function for the AnalyticsEngine."""
    return AnalyticsEngine()
