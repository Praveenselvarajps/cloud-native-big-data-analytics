"""Upload raw sample data to Amazon S3 Raw Data Zone."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import boto3
from config.settings import settings


def upload_raw_dataset() -> bool:
    """Uploads local raw dataset to the configured S3 bucket raw prefix."""
    local_csv = settings.raw_data_dir / "sample_ecommerce_data.csv"
    if not local_csv.exists():
        print(f"[X] Error: Local raw dataset does not exist: {local_csv}")
        print("    Run 'python scripts/generate_sample_data.py' first.")
        return False

    s3_key = f"{settings.s3_raw_prefix}sample_ecommerce_data.csv"
    print("=" * 76)
    print("           UPLOADING RAW DATASET TO AMAZON S3 RAW ZONE")
    print("=" * 76)
    print(f" Source Local File  : {local_csv}")
    print(f" Target S3 Location : s3://{settings.s3_bucket_name}/{s3_key}")
    print("-" * 76)

    try:
        session = boto3.Session(
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        s3 = session.client("s3")
        with open(local_csv, "rb") as f:
            s3.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=f.read(),
                ContentType="text/csv",
            )
        print("[+] SUCCESS: Raw dataset uploaded to Amazon S3!")
        print(f"    Available at: s3://{settings.s3_bucket_name}/{s3_key}")
        print("=" * 76)
        return True
    except Exception as exc:
        print(f"[X] Upload Failed: {exc}")
        print("    Verify your AWS credentials in .env or via 'aws configure'.")
        print("=" * 76)
        return False


if __name__ == "__main__":
    success = upload_raw_dataset()
    sys.exit(0 if success else 1)
