"""Load Module for the ETL Pipeline.

Saves processed datasets to:
1. Local Storage (clean Parquet & CSV, rejected CSV with reasons).
2. Amazon S3 (clean Parquet under processed/ prefix, rejected CSV under rejected/ prefix).

Guarantees idempotency (repeated executions safely overwrite existing artifacts
without creating duplicate rows).
"""
from dataclasses import dataclass
from io import BytesIO
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class LoadResult:
    """Audit summary of load operation."""
    clean_target: str
    rejected_target: str
    clean_records_count: int
    rejected_records_count: int
    format: str


def save_local_clean(
    df: pd.DataFrame,
    output_dir: Path,
    filename_stem: str = "orders_clean",
) -> Path:
    """Save clean records locally in both Parquet (for performance/Athena) and CSV formats.

    Args:
        df: Clean, transformed DataFrame.
        output_dir: Directory to save processed records into.
        filename_stem: Base name for output files.

    Returns:
        Path to the generated Parquet file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / f"{filename_stem}.parquet"
    csv_path = output_dir / f"{filename_stem}.csv"

    # Save as snappy-compressed Parquet using pyarrow engine
    df.to_parquet(parquet_path, index=False, engine="pyarrow", compression="snappy")
    # Also save companion CSV for quick human inspection
    df.to_csv(csv_path, index=False)

    logger.info(f"Saved {len(df)} clean records to {parquet_path} and {csv_path}")
    return parquet_path


def save_local_rejected(
    df: pd.DataFrame,
    output_dir: Path,
    filename_stem: str = "orders_rejected",
) -> Path:
    """Save quarantined invalid records locally as CSV for audit inspection.

    Args:
        df: Quarantined DataFrame with rejection reasons.
        output_dir: Directory to save rejected records into.
        filename_stem: Base name for output file.

    Returns:
        Path to the generated CSV file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{filename_stem}.csv"
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved {len(df)} rejected records with audit reasons to {csv_path}")
    return csv_path


def upload_parquet_to_s3(
    df: pd.DataFrame,
    s3_client,
    bucket: str,
    key: str,
) -> str:
    """Upload DataFrame directly to Amazon S3 as snappy-compressed Parquet.

    Args:
        df: Clean DataFrame.
        s3_client: Initialized Boto3 S3 client.
        bucket: Target S3 bucket name.
        key: Target S3 object key.

    Returns:
        S3 URI string (s3://bucket/key).
    """
    buffer = BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
    buffer.seek(0)
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
    )
    s3_uri = f"s3://{bucket}/{key}"
    logger.info(f"Uploaded {len(df)} clean records to {s3_uri}")
    return s3_uri


def upload_csv_to_s3(
    df: pd.DataFrame,
    s3_client,
    bucket: str,
    key: str,
) -> str:
    """Upload DataFrame directly to Amazon S3 as CSV.

    Args:
        df: DataFrame (e.g., quarantined records).
        s3_client: Initialized Boto3 S3 client.
        bucket: Target S3 bucket name.
        key: Target S3 object key.

    Returns:
        S3 URI string (s3://bucket/key).
    """
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="text/csv",
    )
    s3_uri = f"s3://{bucket}/{key}"
    logger.info(f"Uploaded {len(df)} records to {s3_uri}")
    return s3_uri


def load_clean_data(
    df: pd.DataFrame,
    output_dir: Path,
    is_s3: bool = False,
    s3_client=None,
    s3_bucket: Optional[str] = None,
    s3_key: Optional[str] = None,
) -> str:
    """Load clean data to local disk and optionally to Amazon S3.

    Returns:
        Primary target URI or file path.
    """
    local_path = save_local_clean(df, output_dir)
    if is_s3 and s3_client and s3_bucket and s3_key:
        return upload_parquet_to_s3(df, s3_client, s3_bucket, s3_key)
    return str(local_path)


def load_rejected_data(
    df: pd.DataFrame,
    output_dir: Path,
    is_s3: bool = False,
    s3_client=None,
    s3_bucket: Optional[str] = None,
    s3_key: Optional[str] = None,
) -> str:
    """Load rejected data to local disk and optionally to Amazon S3.

    Returns:
        Primary target URI or file path.
    """
    local_path = save_local_rejected(df, output_dir)
    if is_s3 and s3_client and s3_bucket and s3_key:
        return upload_csv_to_s3(df, s3_client, s3_bucket, s3_key)
    return str(local_path)
