# ==============================================================================
# PRODUCTION DOCKERFILE: CLOUD-NATIVE BIG DATA ANALYTICS PLATFORM
# Multi-stage security and optimization for Streamlit & AWS App Runner hosting
# ==============================================================================

# 1. Base Image: Official lightweight Python 3.11 Debian Slim base
FROM python:3.11-slim-bookworm

# 2. Set container metadata
LABEL maintainer="Cloud & Data Engineering Team"
LABEL description="Cloud-Native Big Data Analytics Dashboard with Athena SQL & S3"

# 3. Security & Python Environment Tuning
# - PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# - PYTHONUNBUFFERED: Flushes stdout and stderr immediately for CloudWatch logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 4. Set dedicated application working directory
WORKDIR /app

# 5. Install system dependencies & curl for healthchecks, then clean package cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 6. Create unprivileged non-root user for enterprise container security
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# 7. Leverage Docker Layer Caching: Copy requirements.txt and install wheels first
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 8. Copy application code and folders
COPY app.py .
COPY config/ config/
COPY etl/ etl/
COPY analytics/ analytics/
COPY scripts/ scripts/

# 9. Create data directory structure for runtime temp files and assign non-root ownership
RUN mkdir -p data/raw data/processed data/rejected && \
    chown -R appuser:appgroup /app

# 10. Switch to unprivileged non-root user
USER appuser

# 11. Expose Streamlit application port
EXPOSE 8501

# 12. Healthcheck instruction to ensure orchestrators (App Runner / ECS) know the container is healthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 13. Container Entrypoint
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
