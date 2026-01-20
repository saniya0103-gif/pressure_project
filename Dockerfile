# Use Raspberry Pi compatible Python 3.11 base image
FROM python:3.11-bullseye

# -----------------------------
# Install system dependencies
# -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    i2c-tools \
    python3-dev \
    gcc \
    libgpiod2 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# -----------------------------
# Install required Python libraries
# -----------------------------
# DO NOT install lgpio manually; Blinka handles GPIO automatically
RUN python3 -m pip install \
    adafruit-blinka \
    adafruit-circuitpython-ads1x15 \
    smbus2 \
    paho-mqtt \
    requests \
    pytz \
    AWSIoTPythonSDK

# Copy project files
COPY . /app

# -----------------------------
# Set Blinka environment variables for Raspberry Pi 5
# -----------------------------
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV BLINKA_USE_LGPIO=1
ENV PYTHONUNBUFFERED=1

# -----------------------------
# Run the main Python script
# -----------------------------
CMD ["python3", "system_convert.py"]
