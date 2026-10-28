# Scheduled ETL Architecture (Amazon EventBridge & Lambda)

This guide documents the automated, hands-off scheduling mechanism for executing the ETL pipeline in the cloud.

---

## 1. Scheduling Architecture

```
[DATA PRODUCER] 
       │ (Uploads raw CSV)
       ▼
[Amazon S3: data/raw/] 
       │
       │ S3 Event (s3:ObjectCreated:*)
       ▼
[Amazon EventBridge / S3 Trigger]
       │
       │ (Or Recurring Cron: cron(0 6 * * ? *))
       ▼
[AWS Lambda / Scheduled Glue / Fargate Task]
       │
       ├── 1. Extract raw CSV from S3
       ├── 2. Validate, Clean & Quarantine
       ├── 3. Load Parquet to data/processed/
       └── 4. Load Rejections to data/rejected/
       │
       ▼
[Amazon CloudWatch] (Logs & Execution Metrics)
```

---

## 2. Event-Driven vs. Time-Based Scheduling

The platform supports two distinct triggering paradigms:

### Paradigm A: Event-Driven Automation (Immediate Processing)
* **Trigger**: Whenever a new CSV file lands inside `s3://<BUCKET>/data/raw/*.csv`.
* **Latency**: Instant execution (starts within seconds of file arrival).
* **Cost Efficiency**: Zero compute cost when no new files arrive.

### Paradigm B: Time-Based Recurring Schedule (Batch Window)
* **Trigger**: Amazon EventBridge Rule with a Cron expression.
* **Example Schedule**: `cron(0 6 * * ? *)` (Runs every morning at 06:00 AM UTC before business hours).
* **Predictability**: Consistent daily analytical snapshot.

---

## 3. IAM Execution Role for Scheduled ETL

To allow Lambda or scheduled compute to execute the pipeline independently:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/data/*"
    }
  ]
}
```

---

## 4. Monitoring & Alerting

* **Amazon CloudWatch Logs**: All ETL steps log structured JSON outputs with record counts and elapsed execution times.
* **CloudWatch Alarms**: Configured to send an Amazon SNS email alert if the pipeline exits with `statusCode != 200` or takes longer than 60 seconds.
