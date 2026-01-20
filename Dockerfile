# Use Raspberry Pi compatible Python 3.11 slim image
FROM python:3.11-slim-bullseye

# -----------------------------
# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    i2c-tools \
    python3-dev \
    gcc \
    build-essential \
    swig \
    libgpiod2 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Set working directory
WORKDIR /app

# -----------------------------
# Clone your public repository
RUN git clone https://github.com/saniya0103-gif/pressure_project.git /app

# -----------------------------
# Upgrade pip and install Python libraries
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install \
    smbus2 \
    paho-mqtt \
    requests \
    pytz \
    AWSIoTPythonSDK \
    adafruit-blinka \
    adafruit-circuitpython-ads1x15 \
    numpy \
    lgpio

# -----------------------------
# Blinka environment variables for Raspberry Pi 5
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV BLINKA_USE_LGPIO=1
ENV PYTHONUNBUFFERED=1

# -----------------------------
# Run the main script
CMD ["python3", "system_convert.py"]
