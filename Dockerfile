FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install required system packages for I2C, sqlite, build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        sqlite3 \
        python3-dev \
        build-essential \
        swig \
        python3-smbus \
        i2c-tools \
        libgpiod-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir awsiotsdk

# Copy all project files
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python", "system_convert.py"]
CMD ["python", "system_upload.py"]
