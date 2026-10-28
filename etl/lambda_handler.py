"""Serverless AWS Lambda Handler for Scheduled ETL Execution.

Can be triggered by:
1. Amazon EventBridge (Cron / Rate schedule, e.g. every morning at 06:00 UTC).
2. Amazon S3 ObjectCreated Event Notifications (when new raw CSVs land in data/raw/).
"""
import json
import logging
from typing import Dict, Any

from etl.pipeline import run_etl_pipeline, PipelineSummary

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Entry point for AWS Lambda / EventBridge invocation."""
    logger.info("Received event for automated ETL trigger: %s", json.dumps(event))

    # Detect if triggered by S3 ObjectCreated event
    input_source = None
    if "Records" in event and len(event["Records"]) > 0:
        record = event["Records"][0]
        if "s3" in record and "object" in record["s3"]:
            s3_key = record["s3"]["object"].get("key")
            logger.info("Triggered by new S3 object upload: %s", s3_key)
            input_source = s3_key

    try:
        # Run pipeline in cloud mode against S3
        summary: PipelineSummary = run_etl_pipeline(
            input_source=input_source,
            is_cloud=True,
        )

        return {
            "statusCode": 200 if summary.status == "SUCCESS" else 500,
            "body": json.dumps({
                "message": f"ETL Pipeline completed with status: {summary.status}",
                "clean_records": summary.clean_records,
                "rejected_records": summary.rejected_records,
                "total_revenue": summary.total_revenue,
                "duration_seconds": summary.duration_seconds,
            }),
        }
    except Exception as exc:
        logger.error("Automated ETL execution failed: %s", exc)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
        }
