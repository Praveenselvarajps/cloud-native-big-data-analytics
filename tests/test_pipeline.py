"""Unit and Integration Tests for the complete ETL Pipeline Orchestrator."""
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd

from etl.extract import (
    extract_from_local_csv,
    MissingColumnsError,
    ExtractError,
    EmptyDatasetError,
)
from etl.pipeline import run_etl_pipeline, PipelineSummary


class TestPipeline(unittest.TestCase):
    """Test suite for ETL extraction and pipeline orchestration."""

    def test_extract_missing_columns_raises_error(self) -> None:
        """Verify that extracting a CSV missing mandatory schema columns raises MissingColumnsError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_csv = Path(tmp_dir) / "missing_cols.csv"
            # Missing customer_id and unit_price
            df = pd.DataFrame({
                "order_id": ["ORD-1"],
                "order_date": ["2026-10-01"],
                "product_id": ["P1"],
                "product_name": ["Prod"],
                "category": ["Electronics"],
                "quantity": ["1"],
                "region": ["North America"],
            })
            df.to_csv(bad_csv, index=False)

            with self.assertRaises(MissingColumnsError):
                extract_from_local_csv(bad_csv)

    def test_extract_non_existent_file_raises_error(self) -> None:
        """Verify that extracting a nonexistent file raises ExtractError."""
        with self.assertRaises(ExtractError):
            extract_from_local_csv("non_existent_file_path.csv")

    def test_extract_empty_file_raises_error(self) -> None:
        """Verify that an empty file raises EmptyDatasetError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_csv = Path(tmp_dir) / "empty.csv"
            empty_csv.touch()
            with self.assertRaises((ExtractError, EmptyDatasetError)):
                extract_from_local_csv(empty_csv)

    def test_run_etl_pipeline_local_end_to_end(self) -> None:
        """Verify complete pipeline execution in local mode without AWS credentials."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out_dir = tmp_path / "processed"

            summary: PipelineSummary = run_etl_pipeline(
                is_cloud=False,
                custom_output_dir=out_dir,
            )

            self.assertEqual(summary.status, "SUCCESS")
            self.assertGreater(summary.input_records, 0)
            self.assertGreater(summary.clean_records, 0)
            self.assertGreater(summary.rejected_records, 0)
            self.assertGreater(summary.total_revenue, 0.0)

            # Check that clean Parquet and CSV files were generated
            clean_parquet = out_dir / "orders_clean.parquet"
            clean_csv = out_dir / "orders_clean.csv"
            self.assertTrue(clean_parquet.exists())
            self.assertTrue(clean_csv.exists())

            # Check that rejected audit CSV was generated
            rejected_csv = tmp_path / "rejected" / "orders_rejected.csv"
            self.assertTrue(rejected_csv.exists())

            # Check that summary JSON was generated and contains valid audit data
            summary_json = out_dir / "latest_etl_summary.json"
            self.assertTrue(summary_json.exists())
            with open(summary_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(data["status"], "SUCCESS")
                self.assertEqual(data["clean_records"], summary.clean_records)


if __name__ == "__main__":
    unittest.main()
