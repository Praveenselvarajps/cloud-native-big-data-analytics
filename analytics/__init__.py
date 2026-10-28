"""Analytics package for SQL queries and Amazon Athena integration."""
from analytics.queries import AnalyticsEngine, get_analytics_engine

__all__ = ["AnalyticsEngine", "get_analytics_engine"]
