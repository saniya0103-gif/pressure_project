# Raspberry Pi compatible Python 3.11 base image
FROM python:3.11-bullseye

# -----------------------------
# Install system dependencies for I2C, GPIO, and lgpio
# -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    i2c-tools \
    python3-dev \
    gcc \
    libgpiod2 \
    build-essential \
    swig \
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
# Copy requirements.txt and install Python dependencies
# -----------------------------
COPY requirements.txt /app/
RUN python3 -m pip install -r requirements.txt

# -----------------------------
# Copy project files
# -----------------------------
COPY . /app

# -----------------------------
# Blinka environment variables for Raspberry Pi 5
# -----------------------------
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV BLINKA_USE_LGPIO=1
ENV PYTHONUNBUFFERED=1

# -----------------------------
# Run main script
# -----------------------------
CMD ["python3", "system_convert.py"]
