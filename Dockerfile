FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    i2c-tools \
    libgpiod-dev \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Install Adafruit Blinka + ADS1115
RUN pip install \
    adafruit-blinka \
    adafruit-circuitpython-ads1x15 \
    RPi.GPIO \
    smbus2 \
    paho-mqtt \
    requests \
    pytz \
    AWSIoTPythonSDK

# Copy project files
COPY . /app

# Environment for Raspberry Pi 5
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV PYTHONUNBUFFERED=1

CMD ["python", "system_convert.py"]
