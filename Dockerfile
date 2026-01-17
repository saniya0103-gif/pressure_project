# Use stable Python version
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies for I2C / GPIO / build tools
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-smbus \
    python3-lgpio \
    liblgpio-dev \
    i2c-tools \
    build-essential \
    git \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python3", "system_upload.py"]
