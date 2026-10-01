# ==============================================================================
# BDS-06: Containerized Application Image
# Multi-purpose image for FastAPI Service and Streamlit Dashboard
# ==============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install essential system dependencies (including CBC solver for PuLP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    coinor-cbc \
    coinor-libcbc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency specifications and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and configuration
COPY app/ app/
COPY data/ data/
COPY experiments/ experiments/
COPY configs/ configs/
COPY monitoring/ monitoring/
COPY scripts/ scripts/

# Create persistent storage directories
RUN mkdir -p data/raw data/processed models logs

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Default entrypoint runs the FastAPI service
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
