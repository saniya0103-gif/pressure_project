FROM ghcr.io/raspberrypi/rpi-python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        i2c-tools \
        python3-dev \
        gcc \
        libgpiod2 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install Python packages (no lgpio pip install)
RUN python3 -m pip install \
    smbus2 \
    paho-mqtt \
    requests \
    pytz \
    AWSIoTPythonSDK \
    adafruit-blinka \
    adafruit-circuitpython-ads1x15

# Copy project files
COPY . /app

# Blinka environment variables
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV BLINKA_USE_LGPIO=1
ENV PYTHONUNBUFFERED=1

# Run main script
CMD ["python3", "system_convert.py"]
