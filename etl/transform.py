"""Transformation and Data Quality Validation Module for the ETL Pipeline.

Implements rigorous data cleaning, validation, quarantine, and metric calculation:
1. Column normalization.
2. Mandatory field validation (missing values check).
3. Business key deduplication (on 'order_id').
4. Strict numeric validation (quantity > 0, unit_price > 0).
5. Robust date parsing and validation.
6. Canonical category normalization.
7. Analytical metric calculation (total_amount, year, month, day, day_name).
8. Quarantine routing: invalid rows never enter clean outputs.
"""
from dataclasses import dataclass, field
import logging
import re
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Standard canonical product categories
CANONICAL_CATEGORIES = {
    "electronics": "Electronics",
    "clothing": "Clothing",
    "home & kitchen": "Home & Kitchen",
    "home kitchen": "Home & Kitchen",
    "books": "Books",
    "fitness": "Fitness",
    "sports & fitness": "Fitness",
    "apparel / clothing": "Clothing",
}

# Mandatory columns that must never be empty or null
MANDATORY_FIELDS = ["order_id", "order_date", "customer_id", "category", "unit_price", "quantity"]


@dataclass
class TransformMetrics:
    """Audit metrics produced during data transformation."""
    input_count: int = 0
    clean_count: int = 0
    rejected_count: int = 0
    missing_values_count: int = 0
    duplicates_count: int = 0
    invalid_quantities_count: int = 0
    invalid_prices_count: int = 0
    invalid_dates_count: int = 0
    total_revenue: float = 0.0
    rejection_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_records": self.input_count,
            "clean_records": self.clean_count,
            "rejected_records": self.rejected_count,
            "missing_values": self.missing_values_count,
            "duplicates": self.duplicates_count,
            "invalid_quantities": self.invalid_quantities_count,
            "invalid_prices": self.invalid_prices_count,
            "invalid_dates": self.invalid_dates_count,
            "total_revenue": round(self.total_revenue, 2),
            "rejection_breakdown": self.rejection_breakdown,
        }


@dataclass
class TransformResult:
    """Output container for the transformation phase."""
    clean_df: pd.DataFrame
    rejected_df: pd.DataFrame
    metrics: TransformMetrics


def normalize_category_name(raw_cat: Any) -> str:
    """Normalize inconsistent category strings to canonical naming."""
    if pd.isna(raw_cat) or not str(raw_cat).strip():
        return ""
    cat_str = str(raw_cat).strip().lower()
    # Normalize common abbreviations / punctuation
    cat_cleaned = re.sub(r"\s+", " ", cat_str)
    if cat_cleaned in CANONICAL_CATEGORIES:
        return CANONICAL_CATEGORIES[cat_cleaned]
    # Check if category contains partial matches
    if "electr" in cat_cleaned:
        return "Electronics"
    if "cloth" in cat_cleaned or "apparel" in cat_cleaned:
        return "Clothing"
    if "kitchen" in cat_cleaned or "home" in cat_cleaned:
        return "Home & Kitchen"
    if "book" in cat_cleaned:
        return "Books"
    if "fit" in cat_cleaned or "sport" in cat_cleaned:
        return "Fitness"
    # Default title casing if unrecognized
    return str(raw_cat).strip().title()


def transform_sales_data(df: pd.DataFrame) -> TransformResult:
    """Transform raw sales DataFrame, quarantine defect rows, and compute metrics.

    Args:
        df: Raw DataFrame from extraction phase.

    Returns:
        TransformResult containing clean DataFrame, rejected DataFrame, and audit metrics.
    """
    logger.info("Beginning data transformation and quality validation...")
    metrics = TransformMetrics(input_count=len(df))

    if df.empty:
        return TransformResult(
            clean_df=pd.DataFrame(),
            rejected_df=pd.DataFrame(columns=list(df.columns) + ["rejection_reason"]),
            metrics=metrics,
        )

    # 1. Normalize column names (strip whitespace, lowercase, replace spaces/dashes with underscores)
    working_df = df.copy()
    working_df.columns = [
        re.sub(r"[\s\-]+", "_", col.strip().lower()) for col in working_df.columns
    ]

    # Preserve original indices and track rejection reasons
    rejection_reasons: Dict[int, str] = {}

    # 2. Check for Missing Values in Mandatory Fields
    for idx, row in working_df.iterrows():
        missing_cols = []
        for col in MANDATORY_FIELDS:
            val = row.get(col)
            if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan":
                missing_cols.append(col)
        if missing_cols:
            reason = f"MISSING_REQUIRED_FIELDS: {', '.join(missing_cols)}"
            rejection_reasons[idx] = reason
            metrics.missing_values_count += 1

    # 3. Business Key Deduplication (on 'order_id')
    # Keep the first seen instance; reject subsequent duplicate order_ids
    seen_order_ids: set = set()
    for idx, row in working_df.iterrows():
        if idx in rejection_reasons:
            continue
        order_id = str(row.get("order_id", "")).strip()
        if order_id in seen_order_ids:
            rejection_reasons[idx] = f"DUPLICATE_ORDER_ID: '{order_id}' already processed"
            metrics.duplicates_count += 1
        else:
            seen_order_ids.add(order_id)

    # 4. Quantity Validation (must be numeric integer and > 0)
    for idx, row in working_df.iterrows():
        if idx in rejection_reasons:
            continue
        qty_raw = str(row.get("quantity", "")).strip()
        try:
            qty_val = float(qty_raw)
            if not qty_val.is_integer() or qty_val <= 0:
                rejection_reasons[idx] = f"INVALID_QUANTITY: Value '{qty_raw}' is not an integer > 0"
                metrics.invalid_quantities_count += 1
        except (ValueError, TypeError):
            rejection_reasons[idx] = f"INVALID_QUANTITY: Value '{qty_raw}' is not numeric"
            metrics.invalid_quantities_count += 1

    # 5. Unit Price Validation (must be numeric float and > 0.0)
    for idx, row in working_df.iterrows():
        if idx in rejection_reasons:
            continue
        price_raw = str(row.get("unit_price", "")).strip()
        try:
            price_val = float(price_raw)
            if price_val <= 0.0:
                rejection_reasons[idx] = f"INVALID_PRICE: Value '{price_raw}' must be > 0.0"
                metrics.invalid_prices_count += 1
        except (ValueError, TypeError):
            rejection_reasons[idx] = f"INVALID_PRICE: Value '{price_raw}' is not numeric"
            metrics.invalid_prices_count += 1

    # 6. Date Parsing & Validation
    parsed_dates: Dict[int, pd.Timestamp] = {}
    for idx, row in working_df.iterrows():
        if idx in rejection_reasons:
            continue
        date_raw = str(row.get("order_date", "")).strip()
        try:
            # Parse datetime using pandas to_datetime
            parsed_dt = pd.to_datetime(date_raw, errors="raise")
            parsed_dates[idx] = parsed_dt
        except Exception:
            rejection_reasons[idx] = f"MALFORMED_DATE: Cannot parse '{date_raw}' as datetime"
            metrics.invalid_dates_count += 1

    # Split into Clean and Rejected partitions
    clean_indices = [i for i in working_df.index if i not in rejection_reasons]
    rejected_indices = [i for i in working_df.index if i in rejection_reasons]

    # Build Rejected DataFrame
    if rejected_indices:
        rejected_df = working_df.loc[rejected_indices].copy()
        rejected_df["rejection_reason"] = [rejection_reasons[i] for i in rejected_indices]
        # Calculate reason frequency breakdown
        for reason in rejected_df["rejection_reason"]:
            prefix = reason.split(":")[0].strip()
            metrics.rejection_breakdown[prefix] = metrics.rejection_breakdown.get(prefix, 0) + 1
    else:
        rejected_df = pd.DataFrame(columns=list(working_df.columns) + ["rejection_reason"])

    # Build Clean DataFrame
    if clean_indices:
        clean_df = working_df.loc[clean_indices].copy()

        # Type casting
        clean_df["quantity"] = clean_df["quantity"].astype(int)
        clean_df["unit_price"] = clean_df["unit_price"].astype(float).round(2)
        clean_df["order_date"] = [parsed_dates[i] for i in clean_indices]

        # Normalize categories
        clean_df["category"] = clean_df["category"].apply(normalize_category_name)

        # Strip remaining string columns
        for col in ["order_id", "product_id", "product_name", "region", "customer_id"]:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].astype(str).str.strip()

        # 7. Derived Analytical Feature Engineering
        clean_df["total_amount"] = (clean_df["quantity"] * clean_df["unit_price"]).round(2)
        clean_df["order_year"] = clean_df["order_date"].dt.year.astype(int)
        clean_df["order_month"] = clean_df["order_date"].dt.month.astype(int)
        clean_df["order_day"] = clean_df["order_date"].dt.day.astype(int)
        clean_df["order_year_month"] = clean_df["order_date"].dt.strftime("%Y-%m")
        clean_df["order_day_name"] = clean_df["order_date"].dt.day_name()

        metrics.total_revenue = float(clean_df["total_amount"].sum())
    else:
        clean_df = pd.DataFrame()

    metrics.clean_count = len(clean_df)
    metrics.rejected_count = len(rejected_df)

    logger.info(
        f"Transformation Complete: Input={metrics.input_count}, "
        f"Clean={metrics.clean_count}, Rejected={metrics.rejected_count}, "
        f"Total Revenue=${metrics.total_revenue:,.2f}"
    )

    return TransformResult(
        clean_df=clean_df,
        rejected_df=rejected_df,
        metrics=metrics,
    )
