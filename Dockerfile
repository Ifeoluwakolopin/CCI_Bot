FROM python:3.11-slim

WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p logs

# Copy the rest of the application
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Command will be specified in docker-compose.yml
CMD ["python3", "app.py"]