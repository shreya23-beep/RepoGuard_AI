FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose Webhook server and Streamlit dashboard ports
EXPOSE 8000 8501

# Default command: launch the FastAPI webhook server
CMD ["python", "-m", "repoguard.cli", "server", "--host", "0.0.0.0", "--port", "8000"]
