"""Centralized settings and environment configuration.

Loads configuration from environment variables or a local .env file.
Provides safe fallbacks for local development while requiring complete
cloud configuration in production mode.
"""
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    # Graceful fallback if python-dotenv is not yet installed in Phase 1
    def load_dotenv(*args, **kwargs):
        pass

# Base project directory (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if it exists
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Application settings schema."""
    # Environment mode: 'development' or 'production'
    app_env: str = os.getenv("APP_ENV", "development").lower()

    # Base Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    processed_data_dir: Path = BASE_DIR / "data" / "processed"
    rejected_data_dir: Path = BASE_DIR / "data" / "rejected"

    # AWS Credentials & Region
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")

    # S3 Storage Configuration
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "my-ecommerce-analytics-bucket")
    s3_raw_prefix: str = os.getenv("S3_RAW_PREFIX", "data/raw/")
    s3_processed_prefix: str = os.getenv("S3_PROCESSED_PREFIX", "data/processed/")
    s3_rejected_prefix: str = os.getenv("S3_REJECTED_PREFIX", "data/rejected/")

    # Athena Configuration
    athena_database: str = os.getenv("ATHENA_DATABASE", "ecommerce_analytics_db")
    athena_table: str = os.getenv("ATHENA_TABLE", "processed_orders")
    athena_output_location: str = os.getenv(
        "ATHENA_OUTPUT_LOCATION",
        f"s3://{os.getenv('S3_BUCKET_NAME', 'my-ecommerce-analytics-bucket')}/athena-results/",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production cloud mode."""
        return self.app_env == "production"

    def validate_production(self) -> None:
        """Validate that all required cloud variables are set for production."""
        if self.is_production:
            if not self.s3_bucket_name or self.s3_bucket_name == "my-ecommerce-analytics-bucket":
                raise ValueError(
                    "Production error: S3_BUCKET_NAME must be set to a valid, unique AWS S3 bucket."
                )


# Singleton instance
settings = Settings()
