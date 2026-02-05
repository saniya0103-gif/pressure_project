# Use official slim Python 3.11 image
FROM python:3.11-slim

# -----------------------------
# Install system dependencies
# -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        i2c-tools \
        python3-dev \
        build-essential \
        gcc \
        git \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Set working directory
# -----------------------------
WORKDIR /app

# -----------------------------
# Upgrade pip
# -----------------------------
RUN python3 -m pip install --upgrade pip

# -----------------------------
# Copy requirements.txt first (cache optimization)
# -----------------------------
COPY requirements.txt /app/

# -----------------------------
# Install Python dependencies
# -----------------------------
RUN python3 -m pip install -r requirements.txt

# -----------------------------
# Copy project files
# -----------------------------
COPY . /app

# -----------------------------
# Blinka environment variables
# -----------------------------
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV BLINKA_USE_RPI_GPIO=1
ENV PYTHONUNBUFFERED=1
