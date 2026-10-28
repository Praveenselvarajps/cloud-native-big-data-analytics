# Cloud Deployment & Hosting Guide (Public HTTPS URL)

This guide documents the production deployment of the **Cloud-Native Big Data Analytics Platform** to cloud hosting services.

---

## 1. Cloud Hosting Evaluation

To make the dashboard accessible via a **public HTTPS URL without depending on `localhost` or the developer's computer**, we evaluated three cloud hosting services:

| Feature / Metric | AWS App Runner | Streamlit Community Cloud (Recommended) | Render / Railway |
| :--- | :--- | :--- | :--- |
| **Compatibility** | High (Runs Docker containers directly) | Native (Built directly for Streamlit) | High (Docker or Python native) |
| **HTTPS Support** | Automated TLS/SSL (`.awsapprunner.com`) | Automated TLS/SSL (`.streamlit.app`) | Automated TLS/SSL (`.onrender.com`) |
| **Pricing / Free Tier**| \$0.007/vCPU-hour + \$0.005/GB-hour | **100% Free** (No credit card required) | Free tier available (sleeps on idle) |
| **S3 & AWS Connectivity**| IAM Role or AWS Credentials in env | Boto3 + Secrets Manager | Environment variables |
| **CI/CD Integration** | Automated redeploy on Git push to `main` | Automated redeploy on Git push to `main` | Webhook / GitHub App |
| **Suitability for Project**| Excellent for AWS-native container hosting | **Best & Fastest for College Evaluation** | Great alternative |

---

## 2. Deploying to Streamlit Community Cloud (Instant Public HTTPS)

Streamlit Community Cloud is the industry-standard hosting platform for Streamlit applications, providing an instant, publicly accessible HTTPS URL.

### Step 2.1: Connect Your GitHub Repository
1. Navigate to: 👉 **[share.streamlit.io](https://share.streamlit.io)**
2. Click **"Continue with GitHub"** and sign in with your GitHub account (`Praveenselvarajps`).
3. Click the **"New app"** button.
4. Fill in the deployment details:
   - **Repository**: `Praveenselvarajps/cloud-native-big-data-analytics`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: `cloud-native-big-data-analytics-praveen` *(or choose your preferred subdomain)*

### Step 2.2: Add AWS S3 Cloud Secrets
Before clicking Deploy, click **Advanced settings...** $\rightarrow$ **Secrets**:
Paste your environment settings into the Secrets box:

```toml
APP_ENV = "production"
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "YOUR_AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "YOUR_AWS_SECRET_ACCESS_KEY"
S3_BUCKET_NAME = "ecommerce-platform-2026-praveen"
S3_RAW_PREFIX = "data/raw/"
S3_PROCESSED_PREFIX = "data/processed/"
S3_REJECTED_PREFIX = "data/rejected/"
ATHENA_DATABASE = "ecommerce_analytics_db"
ATHENA_TABLE = "processed_orders"
ATHENA_OUTPUT_LOCATION = "s3://ecommerce-platform-2026-praveen/athena-results/"
```

5. Click **Save** $\rightarrow$ click **Deploy!**

### Step 2.3: Verification
Streamlit Cloud will:
1. Pull your code from GitHub.
2. Read `requirements.txt` and install all packages.
3. Launch your dashboard and provide a permanent public HTTPS URL:
   `https://cloud-native-big-data-analytics-praveen.streamlit.app`
4. Test opening this URL from your mobile phone or another computer. It runs in the cloud independently of your laptop!

---

## 3. Alternative: Deploying via AWS App Runner

If deploying directly inside AWS via App Runner:
1. Open the [AWS App Runner Console](https://console.aws.amazon.com/apprunner).
2. Click **Create service**.
3. **Source**: Select **Source code repository** $\rightarrow$ connect your GitHub account $\rightarrow$ select `Praveenselvarajps/cloud-native-big-data-analytics`.
4. **Branch**: `main` $\rightarrow$ Deployment trigger: **Automatic**.
5. **Runtime**: Select **Python 3** or **Docker**.
   - Build command: `pip install -r requirements.txt`
   - Start command: `streamlit run app.py --server.port=8501 --server.address=0.0.0.0`
   - Port: `8501`
6. Under **Environment variables**, add:
   - `APP_ENV`: `production`
   - `AWS_REGION`: `us-east-1`
   - `S3_BUCKET_NAME`: `ecommerce-platform-2026-praveen`
7. Click **Deploy**. AWS App Runner will provision the service and provide an official HTTPS URL ending in `awsapprunner.com`.
