# AWS Cloud Configuration Guide (Least-Privilege & Security First)

This guide provides step-by-step instructions for configuring Amazon Web Services (AWS) for the **Cloud-Native Big Data Analytics Platform**.

---

## 1. AWS Account & Security Best Practices

### Step 1.1: AWS Account Selection
- If you don't already have an AWS account, create one at [aws.amazon.com](https://aws.amazon.com).
- AWS provides a **Free Tier** for 12 months, which covers:
  - **Amazon S3**: 5 GB of standard storage, 20,000 GET requests, 2,000 PUT requests per month.
  - **Amazon Athena**: First 1 TB of data scanned per month is **FREE**.

### Step 1.2: Root Account Protection
> [!CAUTION]
> **Never** use your AWS Root user account for daily development, and **never** create Access Keys for the root account!
1. Sign in to the AWS Console as the Root User.
2. Go to **IAM (Identity and Access Management)**.
3. Enable **Multi-Factor Authentication (MFA)** on your Root User using an authenticator app (e.g. Google Authenticator).

---

## 2. Create an IAM User with Least-Privilege Permissions

Instead of using full Administrator access, we create an IAM user scoped strictly to our S3 bucket and Athena database:

1. In the AWS Console, search for **IAM** in the top search bar.
2. Click **Users** in the left sidebar $\rightarrow$ click **Create user**.
3. **User name**: `ecommerce-analytics-dev`
4. Leave *"Provide user access to the AWS Management Console"* unchecked (we only need programmatic API access for the CLI/SDK). Click **Next**.
5. On the Set permissions page, choose **Attach policies directly** $\rightarrow$ click **Create policy**.
6. Switch to the **JSON** tab and paste the exact policy from [`config/aws_iam_policy.json`](../config/aws_iam_policy.json):
   *(Replace `YOUR_UNIQUE_BUCKET_NAME` with your actual bucket name, e.g., `my-ecommerce-analytics-2026-praveen`)*.
7. Click **Next** $\rightarrow$ Policy name: `EcommerceAnalyticsLeastPrivilegePolicy` $\rightarrow$ click **Create policy**.
8. Return to the user creation tab, refresh the policies list, select `EcommerceAnalyticsLeastPrivilegePolicy`, and click **Next** $\rightarrow$ **Create user**.

### Step 2.1: Generate Access Keys
1. Click on your newly created user `ecommerce-analytics-dev`.
2. Go to the **Security credentials** tab.
3. Scroll down to **Access keys** $\rightarrow$ click **Create access key**.
4. Choose **Command Line Interface (CLI)**, check the confirmation box, and click **Next**.
5. Description tag: `VS Code Local Development`.
6. Click **Create access key**.
7. **Copy and save** both the **Access key ID** and **Secret access key** safely. *(AWS will never show the secret key again)*.

---

## 3. Create the Amazon S3 Bucket

Amazon S3 provides cloud object storage with 99.999999999% (11 9's) durability.

You can create the bucket either via AWS Console or automatically via our verification script:

### Method A: Via AWS Console
1. Search for **S3** in the AWS Console.
2. Click **Create bucket**.
3. **Bucket name**: Choose a globally unique name containing only lowercase letters, numbers, and hyphens (e.g., `ecommerce-data-platform-2026-YOUR_NAME`).
4. **AWS Region**: Select `us-east-1` (US East, N. Virginia) or your closest region.
5. **Block Public Access settings**: Keep **Block *all* public access** checked! *(Our analytics platform works securely without exposing your bucket to the public internet)*.
6. **Bucket Versioning**: Keep Disabled (or Enable if you want version history).
7. **Default encryption**: Select **Server-side encryption with Amazon S3 managed keys (SSE-S3 / AES256)**.
8. Click **Create bucket**.

### Step 3.1: Create Required Folder Prefixes
Inside your S3 bucket, click **Create folder** to create these prefixes:
* `data/raw/` (Stores incoming raw CSV datasets)
* `data/processed/` (Stores clean transformed Parquet datasets)
* `data/rejected/` (Stores quarantined records with audit failure logs)
* `athena-results/` (Stores SQL analytical query outputs from Athena)

---

## 4. Difference: Local Developer Credentials vs. Cloud IAM Roles

| Aspect | Local Development (VS Code on Windows) | Cloud Production (App Runner / EC2 / ECS) |
| :--- | :--- | :--- |
| **Authentication** | Long-lived IAM User Access Key & Secret Key | Short-lived, automatically rotated **IAM Roles** |
| **Storage Location** | Local `.env` or `~/.aws/credentials` (git-ignored) | Instance Metadata Service (IMDS) via STS |
| **Security Risk** | Moderate (if leaked in Git, must be revoked) | Extremely Safe (no hardcoded keys exist) |
| **Configuration** | `AWS_ACCESS_KEY_ID` in `.env` | Attached as an IAM Execution Role in AWS |

---

## 5. Configure Your Local Project Environment

1. Copy `.env.example` to `.env` in the project root:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Open `.env` in VS Code and fill in your values:
   ```env
   APP_ENV=production
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=AKIA...YOUR_ACCESS_KEY_ID...
   AWS_SECRET_ACCESS_KEY=...YOUR_SECRET_ACCESS_KEY...
   S3_BUCKET_NAME=your-unique-bucket-name
   S3_RAW_PREFIX=data/raw/
   S3_PROCESSED_PREFIX=data/processed/
   S3_REJECTED_PREFIX=data/rejected/
   ATHENA_DATABASE=ecommerce_analytics_db
   ATHENA_TABLE=processed_orders
   ATHENA_OUTPUT_LOCATION=s3://your-unique-bucket-name/athena-results/
   ```

---

## 6. Verify Cloud Access Automatically

Run our automated verification script:
```powershell
python scripts\verify_aws_connection.py
```

### Expected Output when AWS Credentials are configured:
```text
============================================================================
         AWS CLOUD ENVIRONMENT & S3 ACCESS VERIFICATION
============================================================================
 Target Region        : us-east-1
 Target S3 Bucket     : ecommerce-data-platform-2026-praveen
----------------------------------------------------------------------------
[+] SUCCESS: AWS IAM Identity Verified!
    - Account ID : 123456789012
    - User / ARN : arn:aws:iam::123456789012:user/ecommerce-analytics-dev
[-] Checking S3 Bucket status...
[+] S3 Bucket 'ecommerce-data-platform-2026-praveen' exists and is accessible!
[-] Verifying required S3 folder prefixes:
    - s3://ecommerce-data-platform-2026-praveen/data/raw/ [OK]
    - s3://ecommerce-data-platform-2026-praveen/data/processed/ [OK]
    - s3://ecommerce-data-platform-2026-praveen/data/rejected/ [OK]
    - s3://ecommerce-data-platform-2026-praveen/athena-results/ [OK]
[-] Testing read/write/delete permissions with a test canary object...
[+] CANARY TEST PASSED: Full S3 Read, Write & Delete permissions verified!
============================================================================
 CLOUD VERIFICATION SUCCESSFUL: AWS S3 is ready for ETL & Analytics!
============================================================================
```

---

## 7. Cost Considerations & Free Tier Compliance
* **S3 Storage**: $\approx \$0.023$ per GB/month after 5 GB. (Our 500-record dataset is $< 100$ KB, so cost is $\mathbf{\$0.00}$).
* **S3 PUT/GET Requests**: Included in free tier (our pipeline uses $< 50$ requests per run).
* **Athena Queries**: $\$5.00$ per TB scanned. Parquet format cuts scanned data by $\sim 80-90\%$. First 1 TB/month is free, so cost is $\mathbf{\$0.00}$.

---

## 8. Cleanup Instructions (When Project is Finished)
To completely delete cloud storage and avoid unexpected charges:
```powershell
# Empty and delete the S3 bucket using AWS CLI
aws s3 rm s3://your-unique-bucket-name --recursive
aws s3 rb s3://your-unique-bucket-name
```
Or in the AWS Console:
1. Navigate to **S3** $\rightarrow$ select bucket $\rightarrow$ click **Empty**.
2. Once empty, click **Delete** and confirm.
