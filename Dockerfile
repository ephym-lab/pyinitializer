# ---- Base Stage ----
FROM python:3.13-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required by psycopg2-binary & mysql-connector
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# ---- Dependencies Stage ----
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Application Stage ----
FROM dependencies AS application

# Copy source code from backend directory to current WORKDIR (/backend)
COPY . .

# Expose the API port
EXPOSE 8000

# Run the FastAPI application
# Removed brackets from host address
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]