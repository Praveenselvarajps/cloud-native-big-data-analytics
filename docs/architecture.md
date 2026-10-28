# Cloud-Native Big Data Analytics Platform: Architectural Specification

## 1. System Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │              DATA SOURCE                │
                      │   (E-Commerce Transactions CSV Files)   │
                      └────────────────────┬────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │       AMAZON S3 RAW DATA ZONE           │
                      │    s3://bucket/data/raw/*.csv           │
                      └────────────────────┬────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │        AUTOMATED ETL PIPELINE           │
                      │          (Python 3.11 + Pandas)         │
                      │                                         │
                      │  1. Extract & Schema Enforcement        │
                      │  2. Mandatory Field Validation          │
                      │  3. Business Key Deduplication          │
                      │  4. Numerical Bounds Validation         │
                      │  5. Robust Timestamp Parsing            │
                      │  6. Canonical Category Normalization    │
                      │  7. Analytical Feature Engineering      │
                      └──────────────┬──────────────────┬───────┘
                                     │                  │
                Defective Records    │                  │  Clean Records
                (Quarantine Route)   ▼                  ▼  (Snappy Parquet)
      ┌────────────────────────────────────┐  ┌────────────────────────────────────┐
      │    AMAZON S3 REJECTED ZONE         │  │    AMAZON S3 PROCESSED DATA LAKE   │
      │  s3://bucket/data/rejected/        │  │  s3://bucket/data/processed/       │
      │  orders_rejected.csv               │  │  orders_clean.parquet              │
      └────────────────────────────────────┘  └─────────────────┬──────────────────┘
                                                                │
                                                                ▼
                                              ┌────────────────────────────────────┐
                                              │      AWS GLUE DATA CATALOG         │
                                              │    Database: ecommerce_analytics   │
                                              │    Table: processed_orders         │
                                              └─────────────────┬──────────────────┘
                                                                │
                                                                ▼
                                              ┌────────────────────────────────────┐
                                              │          AMAZON ATHENA             │
                                              │    (Presto Serverless SQL Engine)  │
                                              └─────────────────┬──────────────────┘
                                                                │
                                                                ▼
                                              ┌────────────────────────────────────┐
                                              │     UNIFIED DATA ACCESS LAYER      │
                                              │      (analytics/queries.py)        │
                                              │    Athena Mode / Local Fallback    │
                                              └─────────────────┬──────────────────┘
                                                                │
                                                                ▼
                                              ┌────────────────────────────────────┐
                                              │   STREAMLIT ANALYTICS DASHBOARD    │
                                              │   (KPIs, Plotly, Filters, Audit)   │
                                              └─────────────────┬──────────────────┘
                                                                │
                                                                ▼
                                              ┌────────────────────────────────────┐
                                              │       DOCKER CONTAINER IMAGE       │
                                              │   (python:3.11-slim, non-root user)│
                                              └─────────────────┬──────────────────┘
                                                                │
                                                                ▼
                                              ┌────────────────────────────────────┐
                                              │   CLOUD HOSTING (App Runner /      │
                                              │   Streamlit Cloud) - Public HTTPS  │
                                              └────────────────────────────────────┘
```

---

## 2. Component Responsibilities

1. **Amazon S3 Raw Data Zone**:
   - Ingestion landing zone for raw structured CSV transactions.
   - Encrypted with AES256 server-side encryption with Block Public Access active.

2. **Automated ETL Pipeline**:
   - Reads raw CSVs from S3 (or local disk in development mode).
   - Validates schema against 9 mandatory columns.
   - Quarantines records that fail validation into an audit log with reason tags.
   - Generates derived features: `total_amount = quantity * unit_price`, `order_year`, `order_month`, `order_day`, `order_year_month`, `order_day_name`.

3. **Amazon S3 Processed Data Lake**:
   - Stores processed clean data in **Apache Parquet** format.
   - Uses Snappy compression for optimal storage and read throughput.

4. **AWS Glue Data Catalog & Amazon Athena**:
   - Presto/Trino-based serverless distributed SQL query engine.
   - Queries Parquet partitions directly from S3 without persistent database cluster management.
   - Scans only the specific columns needed for each analytical question.

5. **Unified Data Access Layer (`analytics/queries.py`)**:
   - In production, executes queries on Athena via Boto3 with polling and exponential backoff.
   - In development/testing, executes identical aggregations on local Parquet files via Pandas.
   - Protects dashboard from direct SQL manipulation and guarantees offline testability.

6. **Interactive Streamlit Dashboard (`app.py`)**:
   - Presents Executive KPIs, time-series area charts, category donut charts, and territory heatmaps.
   - Offers real-time date, category, and region filtering.
   - Includes a dedicated Data Quality & Quarantine Audit tab.

7. **Production Docker Container (`Dockerfile`)**:
   - Packages application using lightweight `python:3.11-slim-bookworm`.
   - Runs as unprivileged non-root user `appuser` (UID 1000).
   - Integrates native health checks.

8. **CI/CD Automation (`ci.yml` & `deploy.yml`)**:
   - Automates linting, secret scanning, 29 Pytest tests, and container builds on every commit to GitHub.
