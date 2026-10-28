# College Presentation & Viva Guide: Cloud-Native Big Data Analytics Platform

This document provides a slide-by-slide script, technical explanations, and anticipated viva examination questions for presenting this project.

---

## Slide 1: Title & Introduction
* **Project Title**: Cloud-Native Big Data Analytics Platform with Automated ETL and CI/CD
* **Domain**: Cloud Computing, Big Data Engineering, DevSecOps
* **Presenter**: Praveen Selvaraj (Department of Computer Science & Engineering)
* **Guide / Mentor**: Senior Cloud & Data Engineering Faculty
* **Key Pitch**: An automated enterprise data platform that extracts dirty sales transactions, quarantines data anomalies, stores clean records in an Apache Parquet data lake on Amazon S3, executes serverless SQL queries in Amazon Athena, and presents executive BI insights via a cloud-hosted Streamlit dashboard powered by GitHub Actions CI/CD.

---

## Slide 2: Problem Statement
* **Exponential Data Volume**: Modern e-commerce platforms generate millions of transactions daily across multiple geographical regions.
* **Dirty Data Problem**: Raw real-world datasets are inherently noisy:
  - Missing customer IDs and unit prices.
  - Duplicate orders caused by network retries.
  - Anomalous negative quantities or zero prices.
  - Inconsistent categorization (`" electronics "` vs. `"Electronics"`).
* **High Cloud Costs**: Querying raw CSVs directly in cloud query engines like Amazon Athena costs \$5.00 per TB scanned. Uncompressed CSVs scan every single column, wasting bandwidth and money.
* **Fragile Manual Deployments**: Manual script execution lacks automated regression testing, security scanning, and seamless rollback capabilities.

---

## Slide 3: Objectives of Proposed System
1. **Automated Data Quality & Quarantine**: Implement an intelligent ETL pipeline in Python/Pandas that quarantines defective records to a separate audit zone without crashing the pipeline.
2. **Columnar Data Lake on S3**: Convert clean transactions into Snappy-compressed Apache Parquet format to optimize query speed and cut cloud scan costs by $\sim 85\%$.
3. **Serverless SQL Intelligence**: Integrate Amazon Athena and AWS Glue Data Catalog for interactive SQL queries.
4. **Interactive BI Dashboard**: Build a responsive Streamlit application featuring Executive KPIs, time-series area charts, category donut charts, and territory heatmaps.
5. **DevSecOps CI/CD**: Build GitHub Actions workflows (`ci.yml` and `deploy.yml`) that automate linting, secret scanning, 29 Pytest tests, and container builds on every commit.
6. **Zero Localhost Dependency**: Host the application on a public HTTPS cloud URL.

---

## Slide 4: Existing System vs. Proposed System

| Parameter | Existing / Traditional System | Proposed Cloud-Native System |
| :--- | :--- | :--- |
| **Storage Format** | Uncompressed CSV or relational RDBMS | Columnar Apache Parquet with Snappy compression on Amazon S3 |
| **Data Quality** | Manual data cleaning or dirty data accepted | Automated multi-rule quarantine (invalid prices, negative quantities, nulls) |
| **Query Engine** | Heavy SQL server instances running 24/7 | Serverless Amazon Athena (pay only for bytes queried) |
| **Testing** | Manual testing or no automated test suite | **29 automated Pytest unit and integration tests** |
| **Security** | Hardcoded keys in config files | DevSecOps scanner + `.gitignore` + IAM Least-Privilege policies |
| **Deployment** | Run manually on developer's laptop (`localhost`) | **Automated GitHub Actions CI/CD to Public HTTPS Cloud URL** |

---

## Slide 5: System Architecture Diagram

```
[ RAW CSV TRANSACTIONS ]
          │
          ▼
[ AMAZON S3: RAW DATA ZONE ] (s3://bucket/data/raw/)
          │
          ▼
[ AUTOMATED ETL PIPELINE ] (Python + Pandas)
    ├── 1. Schema Enforcement (Mandatory columns check)
    ├── 2. Quarantine Missing Required Fields
    ├── 3. Deduplicate on Business Key (order_id)
    ├── 4. Numeric Validation (quantity > 0, unit_price > 0.0)
    ├── 5. Timestamp Parsing & Normalization
    ├── 6. Canonical Category Normalization
    └── 7. Feature Engineering (total_amount, year, month, day, day_name)
          │
          ├───► [ S3 REJECTED AUDIT ZONE ] (s3://bucket/data/rejected/orders_rejected.csv)
          │
          ▼
[ AMAZON S3: PROCESSED DATA LAKE ] (s3://bucket/data/processed/orders_clean.parquet)
          │
          ▼
[ AWS GLUE CATALOG & AMAZON ATHENA ] (Serverless SQL Queries)
          │
          ▼
[ STREAMLIT INTERACTIVE DASHBOARD ] (Interactive Plotly Visualizations)
          │
          ▼
[ PRODUCTION DOCKER CONTAINER / PUBLIC HTTPS CLOUD URL ]
```

---

## Slide 6: Technologies & Cloud Services Stack

* **Programming & Processing**: Python 3.11, Pandas, PyArrow, NumPy.
* **Cloud Storage & Database**: Amazon S3 (Standard Storage, SSE-S3 AES256, Block Public Access), AWS Glue Data Catalog.
* **Serverless Analytics**: Amazon Athena (Presto/Trino-based serverless distributed SQL query engine).
* **Visualization**: Streamlit (Reactive UI), Plotly Express (Interactive charts).
* **DevOps & Containers**: Docker (Multi-stage, unprivileged `appuser`), Docker Compose, GitHub Actions.
* **Testing & Quality**: Pytest, Pytest-Mock, Flake8, Pre-commit credential leak auditor.

---

## Slide 7: The Automated ETL & Quarantine Pipeline

The pipeline follows a strict, safe, 3-stage flow:
1. **Extract**:
   - Ingests CSV from local disk or streams directly from Amazon S3 via Boto3.
   - Enforces required schema (`order_id`, `order_date`, `product_id`, `category`, `quantity`, `unit_price`, `region`, `customer_id`).
2. **Transform & Quarantine**:
   - **Missing Values**: Rows with null `customer_id`, `unit_price`, or `category` are quarantined.
   - **Deduplication**: First occurrence of `order_id` is accepted; duplicate order IDs are quarantined.
   - **Bounds Checking**: Quantities $\le 0$ and prices $\le 0.0$ are rejected.
   - **Date Parsing**: Malformed dates (`"99/99/2026"`, `"2026-13-45"`) are quarantined.
   - **Feature Engineering**: Calculates `total_amount = quantity * unit_price`, `order_year`, `order_month`, `order_year_month`, and `order_day_name`.
3. **Load**:
   - Clean data $\rightarrow$ snappy-compressed Parquet.
   - Quarantined data $\rightarrow$ audit CSV with explicit `rejection_reason` for compliance inspection.

---

## Slide 8: Why Apache Parquet Beats CSV for Big Data

1. **Columnar vs. Row Storage**:
   - CSV stores records row-by-row: reading 1 column requires scanning the whole file.
   - Parquet groups data by columns: queries only read the columns requested (**Projection Pushdown**).
2. **Snappy Compression**:
   - Compresses data by $\sim 70-80\%$ while maintaining high decompression speeds.
3. **Athena Query Cost Reduction**:
   - Athena charges \$5.00 per TB scanned.
   - Querying Parquet costs $\sim 85\%$ less than querying raw CSV files.

---

## Slide 9: Amazon Athena Serverless SQL Analytics

Athena queries our processed Parquet data lake using ANSI SQL:
* **Executive KPIs**:
  ```sql
  SELECT ROUND(SUM(total_amount), 2) AS total_revenue,
         COUNT(DISTINCT order_id) AS total_orders,
         ROUND(SUM(total_amount) / COUNT(DISTINCT order_id), 2) AS aov
  FROM ecommerce_analytics_db.processed_orders;
  ```
* **Category Contribution**:
  ```sql
  SELECT category, ROUND(SUM(total_amount), 2) AS revenue,
         ROUND(100.0 * SUM(total_amount) / SUM(SUM(total_amount)) OVER(), 2) AS market_share
  FROM ecommerce_analytics_db.processed_orders
  GROUP BY category ORDER BY revenue DESC;
  ```
* **Top 5 Products**:
  ```sql
  SELECT product_name, category, ROUND(SUM(total_amount), 2) AS revenue
  FROM ecommerce_analytics_db.processed_orders
  GROUP BY product_name, category ORDER BY revenue DESC LIMIT 5;
  ```

---

## Slide 10: Interactive Streamlit Dashboard

* **Executive Metric Cards**: Total Revenue (\$202,427.64), Orders (465), Units (2,100+), AOV (\$435.33).
* **Interactive Tabs**:
  1. *Revenue & Order Trends*: Monthly area chart and day-of-week purchasing patterns.
  2. *Category & Product Insights*: Category market share donut chart and Top 5 products bar chart.
  3. *Regional Performance*: Geographic sales distribution and data table.
  4. *ETL & Data Quality Audit*: Pipeline execution duration, clean vs. rejected counters, and quarantined row inspection table with failure reasons.
* **Dynamic Sidebar Filters**: Real-time filtering by Date Range, Product Category, and Sales Territory.
* **On-Demand Pipeline Execution**: Button to trigger the ETL pipeline live from the web UI.

---

## Slide 11: Continuous Integration & Continuous Deployment (CI/CD)

### GitHub Actions CI Workflow (`ci.yml`)
* **Trigger**: Automated on every push to `main`, `develop`, or Pull Requests.
* **Job 1 (Lint, Audit & Pytest Verification)**:
  - Checks out code and provisions Python 3.11 with pip caching.
  - Runs DevSecOps secret scanner (`check_secrets.py`) $\rightarrow$ blocks any commit containing AWS keys.
  - Runs Flake8 syntax checks.
  - Generates synthetic test dataset and executes automated ETL pipeline.
  - **Executes 29 automated Pytest unit tests**.
  - Archives JUnit test report XML.
* **Job 2 (Docker Image Build Validation)**:
  - Builds production Docker image using Docker Buildx to verify container compile integrity.

---

## Slide 12: Production Dockerization & Security Best Practices

* **Base Image**: `python:3.11-slim-bookworm` (minimal vulnerabilities, small size).
* **Non-Root User**: Runs as unprivileged `appuser` (UID 1000) rather than `root`.
* **Layer Caching**: `requirements.txt` installed before copying application code.
* **Zero Secret Leakage**: `.dockerignore` blocks `.env`, credentials, and local virtual environments.
* **Container Healthcheck**: Native `HEALTHCHECK` probing `http://localhost:8501/_stcore/health`.

---

## Slide 13: Results & Metrics Achieved

* **Dataset Ingestion**: 500 total transactional records ingested.
* **Data Quality Results**:
  - **465 Clean Records Loaded** (450 valid transactions + 15 normalized categories).
  - **35 Defective Records Quarantined**:
    - 8 Invalid Quantities (negative / zero).
    - 10 Missing Mandatory Fields (empty customer, price, category).
    - 5 Malformed / Unparseable Dates.
    - 8 Invalid Unit Prices (negative / zero).
    - 4 Duplicate Order IDs.
* **Total Clean Revenue**: \$202,427.64 calculated.
* **Test Coverage**: **29/29 Automated Tests Passed (100% pass rate)**.
* **CI Execution Duration**: $\sim 35-60$ seconds on GitHub Actions cloud runners.

---

## Slide 14: Screenshots to Capture & Present
1. **VS Code Architecture**: Project folder structure, virtual environment, and settings.
2. **Terminal Output**: Output of `python scripts/run_etl.py` showing ASCII execution audit table.
3. **Pytest Verification**: Terminal screenshot showing `29 passed in X.XXs`.
4. **AWS S3 Console**: Showing bucket `ecommerce-platform-2026-praveen` with `data/raw/`, `data/processed/`, and `data/rejected/`.
5. **Streamlit Web Dashboard**: Overview KPI cards, Monthly trend chart, and Category donut chart.
6. **ETL & Data Quality Audit Tab**: Showing quarantine defect breakdown chart and rejected rows table.
7. **GitHub Actions Workflow**: Green checkmarks (✅) on `ci.yml` showing both jobs passed.

---

## Slide 15: Advantages of the Platform
1. **Data Integrity Guarantee**: Defective records are quarantined with exact failure reasons; invalid data never pollutes analytical insights.
2. **Cost-Optimized Cloud Storage**: Snappy Parquet format reduces cloud scan charges by $\sim 85\%$.
3. **Serverless Scalability**: Zero database server management; S3 and Athena scale elastically to terabytes.
4. **DevSecOps by Default**: Automated scanning prevents credential leakage before code reaches GitHub.
5. **Turnkey CI/CD**: Every code change is automatically tested and containerized in under 2 minutes.

---

## Slide 16: Limitations & Future Enhancements

### Current System Scope
* Batch CSV data ingestion.
* Pandas-based ETL suitable for datasets up to single-node memory capacity ($\sim 10-20$ GB).

### Future Roadmap
1. **Distributed Big Data Engine**: Replace Pandas with **Apache Spark on AWS EMR** or **AWS Glue ETL** for multi-terabyte distributed data processing.
2. **Real-Time Streaming**: Ingest live clickstream transactions using **Amazon Kinesis Data Streams** or Apache Kafka.
3. **Automated ML Forecasts**: Integrate **Amazon Forecast** or Prophet to predict future monthly product demand.
4. **Single Sign-On (SSO)**: Add AWS Cognito user authentication to restrict dashboard access to authorized business analysts.

---

## Slide 17: Conclusion
* Successfully architected and deployed an end-to-end Cloud-Native Big Data Analytics Platform.
* Demonstrated seamless integration across Cloud Storage (Amazon S3), Serverless Analytics (Amazon Athena), Automated Quality ETL (Python/Pandas), Containerization (Docker), and Continuous Integration (GitHub Actions).
* Achieved 100% test pass rate across 29 test suites and deployed to an accessible public cloud environment.

---

## Slide 18: Anticipated Viva / Examination Questions & Model Answers

### Q1: What is the difference between Amazon S3 and a traditional database?
**Answer**: Amazon S3 is an object storage service designed for massive scalability, 99.999999999% durability, and unstructured or semi-structured files (Parquet, CSV, JSON). A traditional database (like MySQL or PostgreSQL) is an OLTP relational database optimized for fast row-level transactional CRUD operations with ACID guarantees.

### Q2: Why did you convert CSV to Apache Parquet instead of querying CSV directly?
**Answer**: CSV is row-oriented and uncompressed, meaning Athena must read the entire file line-by-line across all columns. Parquet is columnar with snappy compression. Queries only scan the specific columns referenced in the `SELECT` and `WHERE` clauses (Projection Pushdown), reducing data scanned by up to $90\%$ and speeding up queries by up to $10\times$.

### Q3: How do you prevent invalid or duplicate data from corrupting your analytics?
**Answer**: Our ETL pipeline implements a defensive quarantine mechanism. During the Transform phase, it checks mandatory fields, deduplicates on the business key `order_id`, validates numeric bounds (`quantity > 0`, `price > 0.0`), and validates date formats. Defective rows are immediately routed to `data/rejected/orders_rejected.csv` with an audit reason tag, ensuring only pristine records enter `orders_clean.parquet`.

### Q4: How does your GitHub Actions CI pipeline guarantee code quality?
**Answer**: The CI pipeline (`ci.yml`) runs on an isolated Ubuntu runner on every push. It runs our secret scanner `check_secrets.py` to prevent credential leaks, runs Flake8 syntax checks, generates test data, executes the ETL pipeline, and runs all 29 Pytest tests. If even a single test fails, the build breaks and the Docker container build is blocked.

### Q5: Why did you configure your Docker container to run as a non-root user?
**Answer**: Running containers as `root` is a major security vulnerability; if a vulnerability exists in any dependency, an attacker could gain root administrative privileges on the host VM. By creating and switching to an unprivileged user `appuser` (UID 1000), we enforce the Principle of Least Privilege.
