-- ==============================================================================
-- AMAZON ATHENA SQL ANALYTICS QUERIES
-- Optimized SQL queries for e-commerce performance analytics.
-- Uses projection pushdown on Parquet columns to minimize scan costs.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Executive Summary KPIs: Total Revenue, Orders, Quantity, and Average Order Value
-- ------------------------------------------------------------------------------
SELECT
    ROUND(SUM(total_amount), 2) AS total_revenue,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(quantity) AS total_quantity_sold,
    ROUND(SUM(total_amount) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS average_order_value
FROM ecommerce_analytics_db.processed_orders
WHERE 1=1;
-- Optional dynamic filters:
-- AND order_date >= TIMESTAMP '2026-07-01 00:00:00'
-- AND order_date <= TIMESTAMP '2026-10-31 23:59:59'
-- AND category = 'Electronics'
-- AND region = 'North America';


-- ------------------------------------------------------------------------------
-- 2. Monthly Revenue and Order Volume Trends
-- ------------------------------------------------------------------------------
SELECT
    order_year_month,
    COUNT(DISTINCT order_id) AS monthly_orders,
    SUM(quantity) AS units_sold,
    ROUND(SUM(total_amount), 2) AS monthly_revenue,
    ROUND(AVG(total_amount), 2) AS avg_transaction_value
FROM ecommerce_analytics_db.processed_orders
GROUP BY order_year_month
ORDER BY order_year_month ASC;


-- ------------------------------------------------------------------------------
-- 3. Category-Wise Performance and Revenue Contribution
-- ------------------------------------------------------------------------------
SELECT
    category,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(quantity) AS units_sold,
    ROUND(SUM(total_amount), 2) AS category_revenue,
    ROUND(
        100.0 * SUM(total_amount) / SUM(SUM(total_amount)) OVER(),
        2
    ) AS revenue_percentage
FROM ecommerce_analytics_db.processed_orders
GROUP BY category
ORDER BY category_revenue DESC;


-- ------------------------------------------------------------------------------
-- 4. Top 5 Best-Selling Products by Revenue
-- ------------------------------------------------------------------------------
SELECT
    product_id,
    product_name,
    category,
    SUM(quantity) AS units_sold,
    ROUND(SUM(total_amount), 2) AS product_revenue,
    ROUND(AVG(unit_price), 2) AS avg_unit_price
FROM ecommerce_analytics_db.processed_orders
GROUP BY product_id, product_name, category
ORDER BY product_revenue DESC
LIMIT 5;


-- ------------------------------------------------------------------------------
-- 5. Regional Revenue and Market Share
-- ------------------------------------------------------------------------------
SELECT
    region,
    COUNT(DISTINCT order_id) AS orders_count,
    ROUND(SUM(total_amount), 2) AS regional_revenue,
    ROUND(
        100.0 * SUM(total_amount) / SUM(SUM(total_amount)) OVER(),
        2
    ) AS regional_market_share
FROM ecommerce_analytics_db.processed_orders
GROUP BY region
ORDER BY regional_revenue DESC;


-- ------------------------------------------------------------------------------
-- 6. Day of Week Order Trends (Peak Buying Behaviors)
-- ------------------------------------------------------------------------------
SELECT
    order_day_name,
    COUNT(DISTINCT order_id) AS orders_count,
    ROUND(SUM(total_amount), 2) AS day_revenue
FROM ecommerce_analytics_db.processed_orders
GROUP BY order_day_name
ORDER BY day_revenue DESC;


-- ------------------------------------------------------------------------------
-- 7. High-Value Customer Activity
-- ------------------------------------------------------------------------------
SELECT
    customer_id,
    COUNT(DISTINCT order_id) AS lifetime_orders,
    SUM(quantity) AS total_items_bought,
    ROUND(SUM(total_amount), 2) AS customer_lifetime_spend
FROM ecommerce_analytics_db.processed_orders
GROUP BY customer_id
ORDER BY customer_lifetime_spend DESC
LIMIT 10;
