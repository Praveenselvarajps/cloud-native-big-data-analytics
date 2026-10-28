"""Cloud-Native Big Data Analytics Platform - Interactive Streamlit Dashboard.

Provides:
1. Executive KPI Summary (Total Revenue, Orders, Quantity, AOV).
2. Interactive Visualizations (Monthly trends, Category share, Top products, Regional sales).
3. Dynamic Sidebar Filters (Date Range, Category, Region).
4. ETL Pipeline & Data Quality Monitoring (Audit status, Quarantined records breakdown).
"""
from datetime import datetime, date
import logging
from pathlib import Path
import sys

# Ensure root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics.queries import get_analytics_engine, AnalyticsEngine
from config.settings import settings
from etl.pipeline import run_etl_pipeline

# Configure page layout and visual identity
st.set_page_config(
    page_title="Cloud-Native Big Data Analytics Platform",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern enterprise look and feel
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .mode-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .mode-cloud {
        background-color: #DEF7EC;
        color: #03543F;
        border: 1px solid #31C48D;
    }
    .mode-local {
        background-color: #E1EFFE;
        color: #1E429F;
        border: 1px solid #76A9FA;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_engine() -> AnalyticsEngine:
    """Cached analytics engine factory."""
    return get_analytics_engine()


def render_sidebar(engine: AnalyticsEngine):
    """Render sidebar filters and pipeline control."""
    st.sidebar.image("https://img.icons8.com/clouds/200/cloud-storage.png", width=90)
    st.sidebar.title("Analytics Controls")

    # Environment Mode Indicator
    if settings.is_production:
        st.sidebar.markdown(
            '<div class="mode-badge mode-cloud">☁️ Cloud Production (Athena)</div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<div class="mode-badge mode-local">💻 Local Dev (Parquet)</div>',
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Filter Dataset")

    # 1. Date Range Filter
    min_date, max_date = engine.get_date_bounds()
    min_d = min_date.date() if isinstance(min_date, datetime) else min_date
    max_d = max_date.date() if isinstance(max_date, datetime) else max_date

    selected_date_range = st.sidebar.date_input(
        "Transaction Date Range",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
    )

    start_date = selected_date_range[0] if len(selected_date_range) > 0 else min_d
    end_date = selected_date_range[1] if len(selected_date_range) > 1 else max_d

    # 2. Category Filter
    categories = ["All"] + engine.get_distinct_categories()
    selected_category = st.sidebar.selectbox("Product Category", options=categories, index=0)

    # 3. Region Filter
    regions = ["All"] + engine.get_distinct_regions()
    selected_region = st.sidebar.selectbox("Sales Territory", options=regions, index=0)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Automated Pipeline")
    if st.sidebar.button("🔄 Trigger ETL Pipeline", use_container_width=True):
        with st.spinner("Executing Extract -> Transform -> Validate -> Load..."):
            try:
                summary = run_etl_pipeline(is_cloud=settings.is_production)
                if summary.status == "SUCCESS":
                    st.sidebar.success(f"ETL Succeeded in {summary.duration_seconds:.2f}s!")
                else:
                    st.sidebar.error("ETL execution failed.")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
        st.rerun()

    return start_date, end_date, selected_category, selected_region


def main():
    engine = get_engine()

    # Sidebar
    start_date, end_date, category, region = render_sidebar(engine)

    # Title Banner
    st.markdown(
        '<div class="main-header">Cloud-Native Big Data Analytics Platform</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Automated E-Commerce Sales ETL, Parquet Data Lake & Amazon Athena SQL Intelligence</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # 1. Executive KPI Summary Cards
    # --------------------------------------------------------------------------
    kpis = engine.get_kpi_summary(
        start_date=start_date,
        end_date=end_date,
        category=category,
        region=region,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Total Sales Revenue",
            value=f"${kpis['total_revenue']:,.2f}",
        )
    with col2:
        st.metric(
            label="Total Orders",
            value=f"{kpis['total_orders']:,}",
        )
    with col3:
        st.metric(
            label="Units Sold",
            value=f"{kpis['total_quantity']:,}",
        )
    with col4:
        st.metric(
            label="Average Order Value (AOV)",
            value=f"${kpis['average_order_value']:,.2f}",
        )

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 2. Analytical Visualizations Tabs
    # --------------------------------------------------------------------------
    tab_trends, tab_category, tab_regional, tab_monitoring = st.tabs(
        [
            "📈 Revenue & Order Trends",
            "🏷️ Category & Product Insights",
            "🌍 Regional Performance",
            "🛡️ ETL & Data Quality Audit",
        ]
    )

    # TAB 1: Trends
    with tab_trends:
        st.subheader("Monthly Revenue Trajectory")
        monthly_df = engine.get_monthly_revenue_trend(
            start_date=start_date,
            end_date=end_date,
            category=category,
            region=region,
        )

        if not monthly_df.empty:
            fig_monthly = px.area(
                monthly_df,
                x="order_year_month",
                y="monthly_revenue",
                title="Monthly Gross Revenue ($)",
                labels={"order_year_month": "Month", "monthly_revenue": "Revenue ($)"},
                color_discrete_sequence=["#2563EB"],
            )
            fig_monthly.update_layout(xaxis_title="Year-Month", yaxis_title="Revenue ($USD)")
            st.plotly_chart(fig_monthly, use_container_width=True)
        else:
            st.info("No data available for selected filter range.")

        # Day of week distribution
        st.subheader("Day-of-Week Purchasing Patterns")
        day_df = engine.get_day_of_week_trends(
            start_date=start_date,
            end_date=end_date,
            category=category,
            region=region,
        )
        if not day_df.empty:
            fig_day = px.bar(
                day_df,
                x="order_day_name",
                y="day_revenue",
                title="Sales Volume by Day of Week",
                labels={"order_day_name": "Day of Week", "day_revenue": "Revenue ($)"},
                color="day_revenue",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig_day, use_container_width=True)

    # TAB 2: Categories and Products
    with tab_category:
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.subheader("Revenue Contribution by Category")
            cat_df = engine.get_category_revenue(
                start_date=start_date,
                end_date=end_date,
                category=category,
                region=region,
            )
            if not cat_df.empty:
                fig_cat = px.pie(
                    cat_df,
                    names="category",
                    values="category_revenue",
                    title="Category Revenue Share (%)",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Prism,
                )
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("No category data available.")

        with col_c2:
            st.subheader("Top 5 Best-Selling Products")
            prod_df = engine.get_top_products(
                limit=5,
                start_date=start_date,
                end_date=end_date,
                category=category,
                region=region,
            )
            if not prod_df.empty:
                fig_prod = px.bar(
                    prod_df,
                    x="product_revenue",
                    y="product_name",
                    orientation="h",
                    title="Top Grossing Products ($)",
                    labels={"product_revenue": "Revenue ($)", "product_name": "Product"},
                    color="product_revenue",
                    color_continuous_scale="Teal",
                )
                fig_prod.update_layout(yaxis={"autorange": "reversed"})
                st.plotly_chart(fig_prod, use_container_width=True)
            else:
                st.info("No product data available.")

    # TAB 3: Regional Performance
    with tab_regional:
        st.subheader("Geographic Revenue Distribution")
        reg_df = engine.get_region_revenue(
            start_date=start_date,
            end_date=end_date,
            category=category,
            region=region,
        )
        if not reg_df.empty:
            fig_reg = px.bar(
                reg_df,
                x="region",
                y="regional_revenue",
                color="region",
                title="Sales Revenue by Territory ($)",
                labels={"region": "Territory", "regional_revenue": "Revenue ($)"},
            )
            st.plotly_chart(fig_reg, use_container_width=True)

            st.dataframe(
                reg_df.rename(
                    columns={
                        "region": "Territory",
                        "regional_revenue": "Revenue ($)",
                        "orders_count": "Orders",
                        "units_sold": "Units Sold",
                        "share_percent": "Market Share (%)",
                    }
                ),
                use_container_width=True,
            )
        else:
            st.info("No regional data available.")

    # TAB 4: ETL & Data Quality Audit
    with tab_monitoring:
        st.subheader("ETL Execution & Data Quarantine Audit")
        stats = engine.get_etl_monitoring_stats()

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.metric("Pipeline Status", stats.get("status", "UNKNOWN"))
        with m_col2:
            st.metric("Total Ingested Records", f"{stats.get('input_records', 0):,}")
        with m_col3:
            st.metric("Clean Records Loaded", f"{stats.get('clean_records', 0):,}")
        with m_col4:
            st.metric(
                "Quarantined Records",
                f"{stats.get('rejected_records', 0):,}",
                delta=f"-{stats.get('rejected_records', 0)} rejected",
                delta_color="inverse",
            )

        st.markdown("---")
        st.subheader("Quarantine Reason Frequency Breakdown")
        breakdown = stats.get("rejection_breakdown", {})
        if breakdown:
            breakdown_df = pd.DataFrame(
                list(breakdown.items()), columns=["Defect Category", "Quarantined Count"]
            ).sort_values("Quarantined Count", ascending=False)

            fig_breakdown = px.bar(
                breakdown_df,
                x="Defect Category",
                y="Quarantined Count",
                color="Defect Category",
                title="Injected Data Quality Defects Detected & Quarantined",
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)

        # Inspect rejected file records
        rejected_file = settings.rejected_data_dir / "orders_rejected.csv"
        if rejected_file.exists():
            st.subheader("Quarantined Audit Sample (Defective Rows Protected from Analytics)")
            rej_data = pd.read_csv(rejected_file)
            st.dataframe(rej_data.head(15), use_container_width=True)
            st.caption(
                "Notice: Defective rows (invalid prices, negative quantities, malformed dates) "
                "are quarantined here with exact failure reasons and never leak into analytical calculations."
            )


if __name__ == "__main__":
    main()
