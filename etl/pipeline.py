"""Automated ETL Pipeline Orchestrator.

Orchestrates the sequential execution of:
1. Extraction (Local CSV or Amazon S3).
2. Transformation, Validation & Quarantine (Pandas & Data Quality Rules).
3. Loading (Parquet & CSV to Local Storage and/or S3).
4. Audit & Quality Metric Reporting.

Supports execution both locally for development/testing and in AWS for cloud production.
"""
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from config.settings import settings
from etl.extract import extract_data, ExtractError
from etl.transform import transform_sales_data, TransformResult
from etl.load import load_clean_data, load_rejected_data

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ETL_Pipeline")


@dataclass
class PipelineSummary:
    """End-of-job execution summary report."""
    status: str
    start_time: str
    end_time: str
    duration_seconds: float
    input_records: int
    clean_records: int
    rejected_records: int
    total_revenue: float
    clean_target: str
    rejected_target: str
    rejection_breakdown: Dict[str, int]
    error_message: Optional[str] = None

    def print_report(self) -> None:
        """Render a readable audit table to stdout."""
        print("\n" + "=" * 76)
        print("                 ETL PIPELINE EXECUTION SUMMARY")
        print("=" * 76)
        print(f" Status                : {self.status.upper()}")
        print(f" Execution Window      : {self.start_time} --> {self.end_time}")
        print(f" Duration              : {self.duration_seconds:.2f} seconds")
        print("-" * 76)
        print(" RECORD COUNTS:")
        print(f"  * Total Input Records : {self.input_records:>8,}")
        print(f"  * Clean Records Loaded: {self.clean_records:>8,} (Valid & Feature-Engineered)")
        print(f"  * Quarantined Records : {self.rejected_records:>8,} (Defects Routed to Audit)")
        print("-" * 76)
        print(f" Total Revenue Cleaned : ${self.total_revenue:>12,.2f}")
        print("-" * 76)
        print(" QUARANTINE BREAKDOWN:")
        if self.rejection_breakdown:
            for reason, count in self.rejection_breakdown.items():
                print(f"  - {reason:<28}: {count:>6}")
        else:
            print("  - None (All records passed data quality checks!)")
        print("-" * 76)
        print(f" Clean Artifact Target : {self.clean_target}")
        print(f" Rejected Audit Target : {self.rejected_target}")
        if self.error_message:
            print(f" ERROR DETAILS         : {self.error_message}")
        print("=" * 76 + "\n")

    def save_json(self, output_path: Path) -> None:
        """Save summary audit report to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "status": self.status,
                    "start_time": self.start_time,
                    "end_time": self.end_time,
                    "duration_seconds": self.duration_seconds,
                    "input_records": self.input_records,
                    "clean_records": self.clean_records,
                    "rejected_records": self.rejected_records,
                    "total_revenue": self.total_revenue,
                    "clean_target": self.clean_target,
                    "rejected_target": self.rejected_target,
                    "rejection_breakdown": self.rejection_breakdown,
                    "error_message": self.error_message,
                },
                f,
                indent=2,
            )


def get_s3_client():
    """Build Boto3 S3 client using explicit or default IAM credentials."""
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        return boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    return boto3.client("s3", region_name=settings.aws_region)


def run_etl_pipeline(
    input_source: Optional[str] = None,
    is_cloud: bool = False,
    custom_output_dir: Optional[Path] = None,
) -> PipelineSummary:
    """Execute the complete Extract, Transform, Validate, and Load pipeline.

    Args:
        input_source: File path (local) or S3 Key. Defaults to settings.
        is_cloud: If True, uses AWS S3 for source and destination.
        custom_output_dir: Optional directory for local output artifacts.

    Returns:
        PipelineSummary with execution audit information.
    """
    start_ts = datetime.utcnow()
    start_time_str = start_ts.strftime("%Y-%m-%d %H:%M:%S UTC")
    perf_start = time.perf_counter()

    logger.info(f"Starting ETL Pipeline in {'CLOUD (S3)' if is_cloud else 'LOCAL'} mode...")

    output_dir = custom_output_dir or settings.processed_data_dir
    rejected_dir = (
        custom_output_dir.parent / "rejected" if custom_output_dir else settings.rejected_data_dir
    )

    s3_client = None
    if is_cloud:
        try:
            s3_client = get_s3_client()
        except Exception as exc:
            logger.error(f"Failed to initialize AWS S3 client: {exc}")
            raise

    # 1. Extraction Stage
    try:
        source = input_source or (
            f"{settings.s3_raw_prefix}sample_ecommerce_data.csv"
            if is_cloud
            else str(settings.raw_data_dir / "sample_ecommerce_data.csv")
        )
        logger.info(f"Stage 1/3: Extracting from {source}...")
        raw_df = extract_data(
            source_path=source,
            is_s3=is_cloud,
            s3_client=s3_client,
            s3_bucket=settings.s3_bucket_name if is_cloud else None,
        )
    except Exception as exc:
        logger.error(f"ETL Extraction Failed: {exc}")
        end_ts = datetime.utcnow()
        summary = PipelineSummary(
            status="FAILED",
            start_time=start_time_str,
            end_time=end_ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
            duration_seconds=time.perf_counter() - perf_start,
            input_records=0,
            clean_records=0,
            rejected_records=0,
            total_revenue=0.0,
            clean_target="N/A",
            rejected_target="N/A",
            rejection_breakdown={},
            error_message=str(exc),
        )
        return summary

    # 2. Transformation & Quality Validation Stage
    logger.info("Stage 2/3: Transforming and validating records...")
    transform_result: TransformResult = transform_sales_data(raw_df)
    clean_df = transform_result.clean_df
    rejected_df = transform_result.rejected_df
    metrics = transform_result.metrics

    # 3. Loading Stage
    logger.info("Stage 3/3: Loading clean and quarantined artifacts...")
    clean_s3_key = f"{settings.s3_processed_prefix}orders_clean.parquet"
    rejected_s3_key = f"{settings.s3_rejected_prefix}orders_rejected.csv"

    clean_target = load_clean_data(
        df=clean_df,
        output_dir=output_dir,
        is_s3=is_cloud,
        s3_client=s3_client,
        s3_bucket=settings.s3_bucket_name,
        s3_key=clean_s3_key,
    )

    rejected_target = load_rejected_data(
        df=rejected_df,
        output_dir=rejected_dir,
        is_s3=is_cloud,
        s3_client=s3_client,
        s3_bucket=settings.s3_bucket_name,
        s3_key=rejected_s3_key,
    )

    end_ts = datetime.utcnow()
    duration = time.perf_counter() - perf_start

    summary = PipelineSummary(
        status="SUCCESS",
        start_time=start_time_str,
        end_time=end_ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
        duration_seconds=duration,
        input_records=metrics.input_count,
        clean_records=metrics.clean_count,
        rejected_records=metrics.rejected_count,
        total_revenue=metrics.total_revenue,
        clean_target=clean_target,
        rejected_target=rejected_target,
        rejection_breakdown=metrics.rejection_breakdown,
    )

    # Save summary report audit file
    summary_path = output_dir / "latest_etl_summary.json"
    summary.save_json(summary_path)
    logger.info(f"Saved ETL execution summary to {summary_path}")

    return summary


def main() -> None:
    """CLI execution entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Cloud-Native E-Commerce ETL Pipeline")
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="Run against Amazon S3 instead of local disk",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Custom path or S3 key to raw input CSV file",
    )
    args = parser.parse_args()

    # If --cloud is specified or APP_ENV=production, run in cloud mode
    is_cloud_mode = args.cloud or settings.is_production

    summary = run_etl_pipeline(input_source=args.input, is_cloud=is_cloud_mode)
    summary.print_report()

    if summary.status != "SUCCESS":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
