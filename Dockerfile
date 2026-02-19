# Use lightweight Python image (ARM compatible)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for ADS1115 & I2C support if needed)
RUN apt-get update && apt-get install -y \
    gcc \
    libgpiod-dev \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create db folder inside container (if not mounted)
RUN mkdir -p db

# Default command (will be overridden by docker-compose)
CMD ["python", "System_capture1.py"]
