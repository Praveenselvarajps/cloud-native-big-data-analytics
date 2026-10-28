"""Synthetic E-Commerce Dataset Generator for Cloud-Native Big Data Analytics.

Generates realistic structured sales data containing both valid records
and intentionally injected data-quality defects (missing values, duplicates,
invalid quantities, invalid prices, malformed dates, and inconsistent casing)
to test and validate the automated ETL cleaning and quarantine pipeline.
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Set random seed for reproducible sample dataset generation
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# Output directory and default filename
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUTPUT_FILE = OUTPUT_DIR / "sample_ecommerce_data.csv"

# Product catalog for generating realistic sales data
PRODUCTS_CATALOG = [
    # (Product ID, Product Name, Standard Category, Unit Price Range)
    ("PROD-101", "Wireless Noise-Canceling Headphones", "Electronics", (79.99, 199.99)),
    ("PROD-102", "Ergonomic Mechanical Keyboard", "Electronics", (59.99, 129.99)),
    ("PROD-103", "4K Ultra HD Gaming Monitor 27-inch", "Electronics", (249.99, 399.99)),
    ("PROD-104", "USB-C Fast Charging Hub", "Electronics", (19.99, 39.99)),
    ("PROD-201", "Organic Cotton Crewneck T-Shirt", "Clothing", (18.50, 32.00)),
    ("PROD-202", "Water-Resistant Running Jacket", "Clothing", (45.00, 89.99)),
    ("PROD-203", "Classic Denim Straight Jeans", "Clothing", (39.99, 69.99)),
    ("PROD-301", "Stainless Steel French Press Coffee Maker", "Home & Kitchen", (24.99, 44.99)),
    ("PROD-302", "Smart Air Purifier with HEPA Filter", "Home & Kitchen", (89.99, 159.99)),
    ("PROD-303", "Non-Stick Ceramic Cookware Set 10-pc", "Home & Kitchen", (99.99, 189.99)),
    ("PROD-401", "Python Cloud Architecture Handbook", "Books", (29.99, 49.99)),
    ("PROD-402", "Distributed Systems in Practice", "Books", (34.99, 54.99)),
    ("PROD-501", "Adjustable Dumbbells Set 50-lb", "Fitness", (149.99, 299.99)),
    ("PROD-502", "Eco-Friendly Yoga Mat 6mm", "Fitness", (22.00, 38.00)),
]

REGIONS = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East"]

# Inconsistent category variations for testing normalization
CATEGORY_VARIATIONS = {
    "Electronics": ["Electronics", "electronics", "  ELECTRONICS  ", "Electr0nics_test"],
    "Clothing": ["Clothing", "clothing", "CLOTHING ", " apparel / clothing "],
    "Home & Kitchen": ["Home & Kitchen", "home & kitchen", "HOME & KITCHEN", "Home Kitchen"],
    "Books": ["Books", "books", " BOOKS "],
    "Fitness": ["Fitness", "fitness", "FITNESS", "Sports & Fitness"],
}


def generate_valid_record(order_index: int, base_date: datetime) -> Dict[str, Any]:
    """Generate a single clean, valid e-commerce order record."""
    order_id = f"ORD-{20260000 + order_index}"
    # Random date within the last 120 days
    delta_days = random.randint(0, 120)
    delta_seconds = random.randint(0, 86400)
    order_timestamp = base_date - timedelta(days=delta_days, seconds=delta_seconds)
    order_date = order_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    product = random.choice(PRODUCTS_CATALOG)
    product_id, product_name, category, price_range = product

    quantity = random.randint(1, 8)
    unit_price = round(random.uniform(*price_range), 2)
    region = random.choice(REGIONS)
    customer_id = f"CUST-{random.randint(1001, 1500)}"

    return {
        "order_id": order_id,
        "order_date": order_date,
        "product_id": product_id,
        "product_name": product_name,
        "category": category,
        "quantity": quantity,
        "unit_price": unit_price,
        "region": region,
        "customer_id": customer_id,
    }


def generate_dataset(
    valid_count: int = 450,
    defect_count: int = 50,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Generate a complete dataset containing valid and intentional defect records.

    Returns:
        Tuple of (list of record dicts, summary count of injected defects).
    """
    base_date = datetime(2026, 10, 25, 12, 0, 0)
    records: List[Dict[str, Any]] = []
    defects_summary: Dict[str, int] = {
        "missing_values": 0,
        "duplicates": 0,
        "invalid_quantities": 0,
        "invalid_prices": 0,
        "invalid_dates": 0,
        "inconsistent_categories": 0,
    }

    # 1. Generate Valid Records
    for i in range(1, valid_count + 1):
        records.append(generate_valid_record(i, base_date))

    # 2. Inject Intentional Defects
    # We distribute defects across multiple categories to thoroughly test the ETL
    defect_order_start = valid_count + 1

    # A. Inconsistent Category variations (e.g., ' electronics ', 'clothing')
    for i in range(15):
        rec = generate_valid_record(defect_order_start + i, base_date)
        cat = rec["category"]
        if cat in CATEGORY_VARIATIONS:
            rec["category"] = random.choice(CATEGORY_VARIATIONS[cat])
        records.append(rec)
        defects_summary["inconsistent_categories"] += 1
    defect_order_start += 15

    # B. Missing Values (e.g. empty customer_id, unit_price, or category)
    for i in range(10):
        rec = generate_valid_record(defect_order_start + i, base_date)
        defect_type = i % 3
        if defect_type == 0:
            rec["customer_id"] = ""  # Empty customer
        elif defect_type == 1:
            rec["unit_price"] = ""   # Empty price
        else:
            rec["category"] = ""     # Empty category
        records.append(rec)
        defects_summary["missing_values"] += 1
    defect_order_start += 10

    # C. Invalid Quantities (negative, zero)
    for i in range(8):
        rec = generate_valid_record(defect_order_start + i, base_date)
        rec["quantity"] = 0 if i % 2 == 0 else -random.randint(1, 5)
        records.append(rec)
        defects_summary["invalid_quantities"] += 1
    defect_order_start += 8

    # D. Invalid Unit Prices (negative, zero)
    for i in range(8):
        rec = generate_valid_record(defect_order_start + i, base_date)
        rec["unit_price"] = 0.0 if i % 2 == 0 else -round(random.uniform(10.0, 50.0), 2)
        records.append(rec)
        defects_summary["invalid_prices"] += 1
    defect_order_start += 8

    # E. Malformed / Unparseable Dates
    bad_dates = ["99/99/2026", "invalid-date", "2026-13-45 25:99:99", "NOT_A_DATE"]
    for i in range(5):
        rec = generate_valid_record(defect_order_start + i, base_date)
        rec["order_date"] = bad_dates[i % len(bad_dates)]
        records.append(rec)
        defects_summary["invalid_dates"] += 1
    defect_order_start += 5

    # F. Duplicate Records (exact clones of existing valid orders)
    for i in range(4):
        # Pick an existing record from the clean pool
        cloned = dict(records[i * 10])
        records.append(cloned)
        defects_summary["duplicates"] += 1

    # Shuffle the records slightly so defects are interspersed realistically
    random.shuffle(records)

    return records, defects_summary


def save_to_csv(records: List[Dict[str, Any]], output_path: Path) -> None:
    """Save records to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "order_id",
        "order_date",
        "product_id",
        "product_name",
        "category",
        "quantity",
        "unit_price",
        "region",
        "customer_id",
    ]

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    """CLI entry point to generate sample data and print summary report."""
    print("=" * 70)
    print("  CLOUD-NATIVE BIG DATA ANALYTICS: SAMPLE DATASET GENERATOR")
    print("=" * 70)

    valid_count = 450
    records, summary = generate_dataset(valid_count=valid_count)
    total_records = len(records)
    total_defects = sum(summary.values())

    save_to_csv(records, DEFAULT_OUTPUT_FILE)

    print(f"\n[+] Generated file: {DEFAULT_OUTPUT_FILE}")
    print(f"[+] Total records generated: {total_records}")
    print(f"    - Clean baseline records: {valid_count}")
    print(f"    - Injected test defects:   {total_defects}\n")
    print("Defect breakdown (designed for ETL validation):")
    for key, count in summary.items():
        print(f"    * {key.replace('_', ' ').title():<26}: {count}")

    print("\n" + "=" * 70)
    print("  Dataset ready for Local & Cloud ETL processing!")
    print("=" * 70)


if __name__ == "__main__":
    main()
