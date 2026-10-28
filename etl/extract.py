"""Extraction module for the ETL pipeline.

Supports extracting datasets from:
1. Local CSV files (for unit testing and local development).
2. Amazon S3 buckets via Boto3 (for cloud production execution).

Validates required column schemas and provides detailed error messages.
"""
from io import BytesIO, StringIO
import logging
from pathlib import Path
from typing import List, Optional, Set, Union
import pandas as pd

logger = logging.getLogger(__name__)

# Expected minimum schema required for processing
REQUIRED_COLUMNS: Set[str] = {
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


class ExtractError(Exception):
    """Base exception for data extraction errors."""
    pass


class MissingColumnsError(ExtractError):
    """Raised when the extracted dataset is missing required schema columns."""
    pass


class EmptyDatasetError(ExtractError):
    """Raised when the extracted dataset contains no records."""
    pass


def validate_schema(df: pd.DataFrame, source_name: str) -> None:
    """Validate that the DataFrame contains all mandatory columns.

    Args:
        df: Input DataFrame to check.
        source_name: Human-readable name or path of the data source for logging.

    Raises:
        EmptyDatasetError: If DataFrame is completely empty.
        MissingColumnsError: If any required column is absent.
    """
    if df.empty:
        raise EmptyDatasetError(f"Data source '{source_name}' contains no records.")

    # Normalize existing columns for whitespace check
    existing_cols = {col.strip() for col in df.columns}
    missing = REQUIRED_COLUMNS - existing_cols

    if missing:
        raise MissingColumnsError(
            f"Data source '{source_name}' is missing mandatory columns: {sorted(list(missing))}. "
            f"Expected schema: {sorted(list(REQUIRED_COLUMNS))}"
        )


def extract_from_local_csv(file_path: Union[str, Path]) -> pd.DataFrame:
    """Extract and load data from a local CSV file.

    Args:
        file_path: Path to the local CSV file.

    Returns:
        pd.DataFrame containing the raw file contents.

    Raises:
        ExtractError: If the file does not exist or cannot be parsed.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise ExtractError(f"Local input file does not exist: {path}")

    logger.info(f"Extracting data from local file: {path}")
    try:
        # Read all columns as string initially to allow robust validation during transform
        df = pd.read_csv(path, dtype=str, skipinitialspace=True)
    except Exception as exc:
        raise ExtractError(f"Failed to parse CSV file '{path}': {str(exc)}") from exc

    validate_schema(df, str(path))
    logger.info(f"Successfully extracted {len(df)} records from {path.name}")
    return df


def extract_from_s3(
    s3_client,
    bucket: str,
    key: str,
) -> pd.DataFrame:
    """Extract and load CSV data from an Amazon S3 object.

    Args:
        s3_client: Initialized Boto3 S3 client.
        bucket: S3 bucket name.
        key: S3 object key (path to CSV file).

    Returns:
        pd.DataFrame containing the raw S3 file contents.

    Raises:
        ExtractError: If S3 download fails or schema is invalid.
    """
    logger.info(f"Extracting data from S3: s3://{bucket}/{key}")
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content_bytes = response["Body"].read()
        df = pd.read_csv(BytesIO(content_bytes), dtype=str, skipinitialspace=True)
    except Exception as exc:
        raise ExtractError(f"Failed to extract s3://{bucket}/{key}: {str(exc)}") from exc

    validate_schema(df, f"s3://{bucket}/{key}")
    logger.info(f"Successfully extracted {len(df)} records from s3://{bucket}/{key}")
    return df


def extract_data(
    source_path: Union[str, Path],
    is_s3: bool = False,
    s3_client=None,
    s3_bucket: Optional[str] = None,
) -> pd.DataFrame:
    """Unified entrypoint for data extraction.

    Args:
        source_path: Local path OR S3 key.
        is_s3: If True, extracts from Amazon S3; otherwise extracts locally.
        s3_client: Optional Boto3 S3 client (required if is_s3=True).
        s3_bucket: S3 bucket name (required if is_s3=True).

    Returns:
        Raw pd.DataFrame.
    """
    if is_s3:
        if not s3_client or not s3_bucket:
            raise ExtractError("s3_client and s3_bucket are required when is_s3=True")
        return extract_from_s3(s3_client=s3_client, bucket=s3_bucket, key=str(source_path))
    return extract_from_local_csv(file_path=source_path)
