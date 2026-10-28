# Cloud-Native Big Data Analytics Platform with Automated ETL and CI/CD

[![Continuous Integration (CI)](https://github.com/Praveenselvarajps/cloud-native-big-data-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/Praveenselvarajps/cloud-native-big-data-analytics/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Storage Format](https://img.shields.io/badge/storage-Apache%20Parquet%20(Snappy)-orange)](https://parquet.apache.org/)
[![Cloud Provider](https://img.shields.io/badge/cloud-Amazon%20Web%20Services-yellow)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 1. Project Overview & Problem Statement

Modern enterprise e-commerce platforms generate continuous streams of transactional data. However, traditional analytics architectures suffer from three critical bottlenecks:
1. **Dirty Data Pollution**: Duplicate orders, missing values, malformed dates, and anomalous prices contaminate analytical reports.
2. **High Cloud Query Costs**: Querying massive uncompressed CSV files in cloud query engines like Amazon Athena incurs steep network bandwidth and per-byte scanned charges.
3. **Manual Deployments & Lack of CI/CD**: Deploying analytical dashboards manually increases deployment downtime and risks credential exposure.

### Objectives
This project implements an end-to-end, production-grade **Cloud-Native Big Data Analytics Platform** that:
* Ingests structured e-commerce transactions into **Amazon S3**.
* Automatically cleans, validates, deduplicates, and quarantines defective records using **Python and Pandas**.
* Converts clean data into **Snappy-compressed Apache Parquet** files, reducing storage volume and Athena scan costs by $\sim 85\%$.
* Enables interactive serverless SQL querying via **Amazon Athena** and **AWS Glue Data Catalog**.
* Serves dynamic executive visualizations through an interactive **Streamlit Dashboard**.
* Guarantees software quality using **29 automated Pytest unit tests**.
* Automates continuous testing, secret auditing, container building, and deployment using **GitHub Actions CI/CD**.
* Deploys to a **public cloud HTTPS URL** independent of `localhost`.

---

## 2. Cloud Architecture Diagram

```
[ DATA SOURCE ]
       │
       ▼
[ RAW CSV DATASET ] 
       │
       ▼
[ AMAZON S3: RAW DATA ZONE ] (s3://bucket/data/raw/)
       │
       ▼
[ AUTOMATED ETL PIPELINE ] (Python + Pandas)
       ├── 1. Extract & Schema Enforcement
       ├── 2. Mandatory Field Validation (Quarantine Nulls)
       ├── 3. Business Key Deduplication (order_id)
       ├── 4. Numeric Bounds Check (quantity > 0, price > 0)
       ├── 5. Timestamp Parsing & Normalization
       ├── 6. Canonical Category Normalization
       └── 7. Feature Engineering (total_amount, year, month, day, day_name)
       │
       ├───► [ S3 REJECTED ZONE ] (s3://bucket/data/rejected/orders_rejected.csv)
       │
       ▼
[ AMAZON S3: PROCESSED DATA ZONE ] (s3://bucket/data/processed/orders_clean.parquet)
       │
       ▼
[ AWS GLUE DATA CATALOG & AMAZON ATHENA ] (Serverless SQL Analytics)
       │
       ▼
[ UNIFIED ANALYTICS DATA ACCESS LAYER ] (analytics/queries.py)
       │
       ▼
[ STREAMLIT INTERACTIVE DASHBOARD ]
       │
       ▼
[ DOCKER CONTAINER / CLOUD HOSTING ]
       │
       ▼
[ PUBLIC CLOUD HTTPS URL ]
```

---

## 3. Technologies Used

* **Languages & Frameworks**: Python 3.11 / 3.12, Pandas, PyArrow, Streamlit, Plotly.
* **Cloud & Serverless Infrastructure**: Amazon S3, Amazon Athena, AWS Glue Data Catalog, AWS IAM, AWS STS.
* **DevOps & Containers**: Docker, Dockerfile (Non-Root User), Docker Compose, GitHub Actions.
* **Code Quality & DevSecOps**: Pytest, Pytest-Mock, Flake8, Custom Credential Leak Scanner (`check_secrets.py`).

---

## 4. Project Directory Structure

```
cloud-native-big-data-analytics/
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Continuous Integration workflow (Lint, Test, Docker Build)
│       └── deploy.yml                 # Continuous Deployment workflow (Staging/Production)
│
├── analytics/
│   ├── __init__.py                    # Exports AnalyticsEngine and factory
│   ├── athena_ddl.sql                 # Athena database and external Parquet table DDL
│   ├── athena_queries.sql             # Analytical SQL queries (KPIs, trends, top products)
│   └── queries.py                     # Python Data Access Layer (Athena + Local Parquet fallback)
│
├── config/
│   ├── __init__.py                    # Config init
│   ├── aws_iam_policy.json            # Least-privilege IAM policy document
│   └── settings.py                    # Centralized settings & environment loader
│
├── data/
│   ├── raw/                           # Raw incoming CSV files
│   ├── processed/                     # Clean snappy Parquet and CSV files
│   └── rejected/                      # Quarantined invalid records with failure audit logs
│
├── docs/
│   ├── architecture.md                # Comprehensive architectural specification
│   ├── aws_setup_guide.md             # Beginner guide for AWS Console & CLI configuration
│   ├── deployment.md                  # Public HTTPS cloud deployment guide
│   ├── scheduled_etl.md               # EventBridge & Lambda scheduled processing
│   └── presentation.md                # Complete presentation slides & viva guide
│
├── etl/
│   ├── __init__.py                    # Exports ETL modules
│   ├── extract.py                     # Schema validation & ingestion (Local CSV & S3)
│   ├── transform.py                   # Data cleaning, deduplication, quarantine & metrics
│   ├── load.py                        # Parquet / CSV loader (Local & S3)
│   ├── pipeline.py                    # Pipeline orchestrator & audit summary reporter
│   └── lambda_handler.py              # Serverless AWS Lambda handler for scheduled runs
│
├── scripts/
│   ├── __init__.py                    # Scripts init
│   ├── check_secrets.py               # Pre-commit credential and secret leak scanner
│   ├── generate_sample_data.py        # Synthetic dataset generator with injected test defects
│   ├── run_athena_setup.py            # CLI script to create Athena database & table
│   ├── run_etl.py                     # CLI entrypoint to trigger ETL locally or in AWS
│   ├── upload_raw_data_to_s3.py       # Uploads local raw data to Amazon S3
│   └── verify_aws_connection.py       # Automated STS identity & S3 canary verification
│
├── tests/
│   ├── __init__.py                    # Test suite init
│   ├── test_analytics.py              # 10 unit tests for analytical calculations & filters
│   ├── test_app.py                    # Tests verifying Streamlit app import & syntax
│   ├── test_data_generation.py        # Tests verifying synthetic data generator & schema
│   ├── test_docker_config.py          # Tests verifying Dockerfile security & .dockerignore
│   ├── test_pipeline.py               # Integration tests for end-to-end pipeline execution
│   ├── test_security_audit.py         # Tests verifying zero hardcoded credentials
│   └── test_transform.py              # 8 unit tests for all validation & quarantine rules
│
├── .dockerignore                      # Excludes secrets, caches, and venv from container
├── .env.example                       # Environment template for AWS & pipeline settings
├── .gitignore                         # Protects .env, venv/, and caches from Git
├── app.py                             # Interactive Streamlit dashboard application
├── Dockerfile                         # Production-grade multi-stage container build
└── requirements.txt                   # Pinned dependency requirements
```

---

## 5. Local Setup & Execution Guide (Windows / PowerShell)

### Step 5.1: Clone and Set Up Virtual Environment
```powershell
# Clone the repository
git clone https://github.com/Praveenselvarajps/cloud-native-big-data-analytics.git
cd cloud-native-big-data-analytics

# Create and activate Python virtual environment
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

# Install project dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5.2: Generate Sample Dataset
```powershell
python scripts\generate_sample_data.py
```
*Generates 500 records: 450 clean transactions and 50 intentionally defective records (missing values, duplicates, negative quantities, negative prices, and malformed dates).*

### Step 5.3: Execute the Automated ETL Pipeline
```powershell
python scripts\run_etl.py
```
*Processes the raw CSV, normalizes casing, quarantines 35 defective records to `data/rejected/orders_rejected.csv`, and writes 465 clean rows to `data/processed/orders_clean.parquet`.*

### Step 5.4: Launch the Streamlit Dashboard
```powershell
streamlit run app.py
```
*Opens your web browser to `http://localhost:8501` displaying the interactive dashboard.*

### Step 5.5: Run the Complete Automated Test Suite
```powershell
pytest -v tests/
```
*Executes all 29 automated tests (100% passing).*

---

## 6. Cloud Deployment & Public HTTPS Access

### Method A: Streamlit Community Cloud (Recommended & 100% Free)
1. Sign in to [share.streamlit.io](https://share.streamlit.io) with GitHub.
2. Select repository `Praveenselvarajps/cloud-native-big-data-analytics`, branch `main`, main file `app.py`.
3. In **Advanced settings $\rightarrow$ Secrets**, provide your AWS S3 bucket name and read credentials.
4. Click **Deploy** to receive a public HTTPS URL:
   `https://cloud-native-big-data-analytics-praveen.streamlit.app`

### Method B: AWS App Runner Container Deployment
1. Navigate to AWS App Runner in the AWS Management Console.
2. Link your GitHub repository and select the `Dockerfile`.
3. Configure environment variables (`S3_BUCKET_NAME`, `AWS_REGION`).
4. Click **Deploy** to receive an official HTTPS URL ending in `awsapprunner.com`.

---

## 7. Cost Considerations & Free Tier Compliance

| Service | Free Tier Allocation | Estimated Monthly Cost |
| :--- | :--- | :--- |
| **Amazon S3** | 5 GB storage, 20,000 GET, 2,000 PUT requests/month | **\$0.00** (Dataset is $< 200$ KB) |
| **Amazon Athena** | First 1 TB of data scanned per month is **FREE** | **\$0.00** (Parquet queries scan $< 1$ MB) |
| **GitHub Actions** | 2,000 free build minutes/month for public repos | **\$0.00** (Our CI run takes $\approx 1$ minute) |
| **Streamlit Cloud** | Free public application hosting with automated TLS | **\$0.00** |

---

## 8. Resource Cleanup Instructions

When the project is completed, delete all cloud resources with these commands:
```powershell
# Empty and delete the S3 bucket
aws s3 rm s3://YOUR_S3_BUCKET_NAME --recursive
aws s3 rb s3://YOUR_S3_BUCKET_NAME
```
