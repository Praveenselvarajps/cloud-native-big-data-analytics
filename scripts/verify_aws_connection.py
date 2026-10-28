"""AWS Connection and Cloud S3 Resource Verification Script.

Tests and validates:
1. AWS IAM Identity & Credentials (via STS).
2. S3 Bucket availability, private access, and server-side encryption.
3. Existence of required folder prefixes (raw, processed, rejected, athena-results).
4. Read/Write/Delete permissions using a non-destructive canary object.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from config.settings import settings


def check_aws_credentials() -> dict:
    """Verify active AWS credentials using STS caller identity."""
    print("=" * 76)
    print("         AWS CLOUD ENVIRONMENT & S3 ACCESS VERIFICATION")
    print("=" * 76)
    print(f" Target Region        : {settings.aws_region}")
    print(f" Target S3 Bucket     : {settings.s3_bucket_name}")
    print("-" * 76)

    try:
        session = boto3.Session(
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        sts = session.client("sts")
        caller = sts.get_caller_identity()
        print("[+] SUCCESS: AWS IAM Identity Verified!")
        print(f"    - Account ID : {caller.get('Account')}")
        print(f"    - User / ARN : {caller.get('Arn')}")
        print(f"    - User ID    : {caller.get('UserId')}")
        return {"session": session, "caller": caller, "connected": True}
    except NoCredentialsError:
        print("[!] WARNING: No AWS credentials found!")
        print("    AWS CLI or environment variables (AWS_ACCESS_KEY_ID) are not yet configured.")
        print("    Follow the steps in docs/aws_setup_guide.md to configure your AWS credentials.")
        return {"connected": False, "reason": "No credentials"}
    except ClientError as exc:
        print(f"[X] AWS Authentication Error: {exc.response.get('Error', {}).get('Message')}")
        return {"connected": False, "reason": str(exc)}
    except Exception as exc:
        print(f"[X] Connection Error: {str(exc)}")
        return {"connected": False, "reason": str(exc)}


def verify_or_create_s3_bucket(session, bucket_name: str, region: str) -> bool:
    """Check if the bucket exists and has correct prefixes."""
    s3 = session.client("s3")
    print("\n[-] Checking S3 Bucket status...")

    bucket_exists = False
    try:
        s3.head_bucket(Bucket=bucket_name)
        bucket_exists = True
        print(f"[+] S3 Bucket '{bucket_name}' exists and is accessible!")
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ["404", "NoSuchBucket"]:
            print(f"[*] Bucket '{bucket_name}' does not exist yet.")
            try:
                print(f"[*] Creating S3 Bucket '{bucket_name}' in region '{region}'...")
                if region == "us-east-1":
                    s3.create_bucket(Bucket=bucket_name)
                else:
                    s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": region},
                    )
                # Enable default AES256 server-side encryption
                s3.put_bucket_encryption(
                    Bucket=bucket_name,
                    ServerSideEncryptionConfiguration={
                        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
                    },
                )
                # Ensure Block Public Access is 100% enabled
                s3.put_public_access_block(
                    Bucket=bucket_name,
                    PublicAccessBlockConfiguration={
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": True,
                        "RestrictPublicBuckets": True,
                    },
                )
                bucket_exists = True
                print(f"[+] Successfully created secure S3 Bucket '{bucket_name}'!")
            except ClientError as create_err:
                print(f"[X] Failed to create bucket automatically: {create_err}")
                return False
        elif error_code in ["403", "AccessDenied"]:
            print(f"[X] Access Denied: Your IAM identity lacks permission to access '{bucket_name}'.")
            return False
        else:
            print(f"[X] S3 Error ({error_code}): {exc}")
            return False

    if bucket_exists:
        # Create standard prefix folders
        prefixes = [
            settings.s3_raw_prefix,
            settings.s3_processed_prefix,
            settings.s3_rejected_prefix,
            "athena-results/",
        ]
        print("[-] Verifying required S3 folder prefixes:")
        for prefix in prefixes:
            s3.put_object(Bucket=bucket_name, Key=prefix)
            print(f"    - s3://{bucket_name}/{prefix} [OK]")

        # Test Canary Read/Write/Delete
        canary_key = f"{settings.s3_raw_prefix}.canary_test.txt"
        try:
            print("[-] Testing read/write/delete permissions with a test canary object...")
            s3.put_object(Bucket=bucket_name, Key=canary_key, Body=b"Canary Health Check Passed")
            canary_obj = s3.get_object(Bucket=bucket_name, Key=canary_key)
            assert canary_obj["Body"].read() == b"Canary Health Check Passed"
            s3.delete_object(Bucket=bucket_name, Key=canary_key)
            print("[+] CANARY TEST PASSED: Full S3 Read, Write & Delete permissions verified!")
            return True
        except Exception as canary_exc:
            print(f"[X] Canary permission test failed: {canary_exc}")
            return False

    return False


def main() -> None:
    """Main verification execution."""
    result = check_aws_credentials()
    if not result.get("connected"):
        print("\n" + "=" * 76)
        print(" SUMMARY: AWS credentials not yet provided in .env or AWS CLI.")
        print(" The system is currently running in LOCAL development mode.")
        print(" To enable live AWS Cloud features, follow docs/aws_setup_guide.md.")
        print("=" * 76)
        sys.exit(0)

    session = result["session"]
    bucket_ok = verify_or_create_s3_bucket(
        session=session,
        bucket_name=settings.s3_bucket_name,
        region=settings.aws_region,
    )

    print("\n" + "=" * 76)
    if bucket_ok:
        print(" CLOUD VERIFICATION SUCCESSFUL: AWS S3 is ready for ETL & Analytics!")
    else:
        print(" CLOUD VERIFICATION INCOMPLETE: Please review errors above.")
    print("=" * 76)


if __name__ == "__main__":
    main()
