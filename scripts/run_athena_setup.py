"""Automated AWS Athena Database and Table Setup Script.

Executes the DDL statements from analytics/athena_ddl.sql against Amazon Athena,
creating the Glue database and external Parquet table pointing to your S3 bucket.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config.settings import settings


def run_query(athena, query: str, database: str = "default") -> dict:
    """Execute a single query in Athena and poll until completion."""
    resp = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": settings.athena_output_location},
    )
    qid = resp["QueryExecutionId"]
    while True:
        status = athena.get_query_execution(QueryExecutionId=qid)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            return {"status": "SUCCEEDED", "qid": qid}
        elif state in ["FAILED", "CANCELLED"]:
            reason = status["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
            raise RuntimeError(f"Athena query failed ({state}): {reason}")
        time.sleep(1)


def setup_athena() -> None:
    """Set up Athena Database and Parquet Table."""
    print("=" * 76)
    print("        AMAZON ATHENA GLUE DATABASE & TABLE SETUP")
    print("=" * 76)
    print(f" Target Database : {settings.athena_database}")
    print(f" Target Table    : {settings.athena_table}")
    print(f" S3 Location     : s3://{settings.s3_bucket_name}/{settings.s3_processed_prefix}")
    print(f" Query Results   : {settings.athena_output_location}")
    print("-" * 76)

    try:
        session = boto3.Session(
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        athena = session.client("athena")
        # Quick test call
        athena.list_work_groups()
    except (NoCredentialsError, ClientError) as exc:
        print("[!] NOTICE: Live AWS credentials not currently configured.")
        print("    You can run this script later once credentials are provided in .env.")
        print("\n    To run manually in AWS Console:")
        print("    1. Navigate to Amazon Athena -> Query Editor.")
        print(f"    2. Set query result location to: {settings.athena_output_location}")
        print("    3. Copy and run the SQL from: analytics/athena_ddl.sql")
        print("=" * 76)
        return

    # 1. Create Database
    db_sql = f"CREATE DATABASE IF NOT EXISTS {settings.athena_database};"
    print(f"[-] Creating database '{settings.athena_database}'...")
    try:
        run_query(athena, db_sql)
        print(f"[+] Database '{settings.athena_database}' created / verified.")
    except Exception as exc:
        print(f"[X] Database creation failed: {exc}")
        return

    # 2. Create External Table on Parquet
    s3_data_location = f"s3://{settings.s3_bucket_name}/{settings.s3_processed_prefix}"
    table_sql = f"""
    CREATE EXTERNAL TABLE IF NOT EXISTS {settings.athena_database}.{settings.athena_table} (
        order_id STRING,
        order_date TIMESTAMP,
        product_id STRING,
        product_name STRING,
        category STRING,
        quantity INT,
        unit_price DOUBLE,
        region STRING,
        customer_id STRING,
        total_amount DOUBLE,
        order_year INT,
        order_month INT,
        order_day INT,
        order_year_month STRING,
        order_day_name STRING
    )
    STORED AS PARQUET
    LOCATION '{s3_data_location}'
    TBLPROPERTIES ('parquet.compress' = 'SNAPPY');
    """
    print(f"[-] Creating external table '{settings.athena_table}' pointing to {s3_data_location}...")
    try:
        run_query(athena, table_sql, database=settings.athena_database)
        print(f"[+] External table '{settings.athena_table}' successfully created!")
    except Exception as exc:
        print(f"[X] Table creation failed: {exc}")
        return

    # 3. Test verification query
    count_sql = f"SELECT count(*) AS total_count FROM {settings.athena_database}.{settings.athena_table};"
    print("[-] Testing Athena query execution with COUNT(*)...")
    try:
        q_res = run_query(athena, count_sql, database=settings.athena_database)
        results = athena.get_query_results(QueryExecutionId=q_res["qid"])
        rows = results["ResultSet"]["Rows"]
        count_val = rows[1]["Data"][0]["VarCharValue"] if len(rows) > 1 else "0"
        print(f"[+] ATHENA QUERY SUCCEEDED! Total processed rows in S3: {count_val}")
    except Exception as exc:
        print(f"[!] Warning: Count query failed ({exc}). Make sure Parquet files are uploaded to S3.")

    print("\n" + "=" * 76)
    print(" ATHENA CONFIGURATION COMPLETE!")
    print("=" * 76)


if __name__ == "__main__":
    setup_athena()
