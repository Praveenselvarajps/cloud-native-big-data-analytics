-- ==============================================================================
-- AMAZON ATHENA DDL (DATA DEFINITION LANGUAGE)
-- Database & External Table Definitions for E-Commerce Parquet Analytics
-- ==============================================================================

-- 1. Create the Analytics Database in AWS Glue Data Catalog
CREATE DATABASE IF NOT EXISTS ecommerce_analytics_db
COMMENT 'Central database for Cloud-Native E-Commerce Big Data Analytics'
LOCATION 's3://YOUR_S3_BUCKET_NAME/athena-metadata/';

-- 2. Drop existing table if schema changed
-- DROP TABLE IF EXISTS ecommerce_analytics_db.processed_orders;

-- 3. Create External Table on Snappy-Compressed Parquet Processed Data
-- Note: Replace YOUR_S3_BUCKET_NAME with your actual S3 bucket name.
CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_analytics_db.processed_orders (
    order_id STRING COMMENT 'Unique identifier for each transaction order',
    order_date TIMESTAMP COMMENT 'Timestamp of transaction in ISO format',
    product_id STRING COMMENT 'Unique product SKU identifier',
    product_name STRING COMMENT 'Full product display name',
    category STRING COMMENT 'Normalized canonical product category',
    quantity INT COMMENT 'Number of units purchased (integer > 0)',
    unit_price DOUBLE COMMENT 'Price per single unit in USD',
    region STRING COMMENT 'Geographic sales territory',
    customer_id STRING COMMENT 'Unique customer identifier',
    total_amount DOUBLE COMMENT 'Engineered metric: quantity * unit_price',
    order_year INT COMMENT 'Extracted year of purchase (e.g. 2026)',
    order_month INT COMMENT 'Extracted month of purchase (1-12)',
    order_day INT COMMENT 'Extracted day of purchase (1-31)',
    order_year_month STRING COMMENT 'Extracted Year-Month string (e.g. 2026-08)',
    order_day_name STRING COMMENT 'Name of weekday (e.g. Saturday, Monday)'
)
STORED AS PARQUET
LOCATION 's3://YOUR_S3_BUCKET_NAME/data/processed/'
TBLPROPERTIES (
    'parquet.compress' = 'SNAPPY',
    'classification' = 'parquet',
    'has_encrypted_data' = 'false'
);

-- 4. Verify table registration and preview records
SELECT * 
FROM ecommerce_analytics_db.processed_orders 
LIMIT 10;
