FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    i2c-tools \
    python3-dev \
    gcc \
     libgpiod2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

#RUN pip install --upgrade pip

# Upgrade pip
# -----------------------------
RUN python3 -m pip install --upgrade pip

# Install ONLY required Python libs
RUN pip install \
    smbus2 \
    paho-mqtt \
    requests \
    pytz \
    AWSIoTPythonSDK \
    adafruit-blinka \
    adafruit-circuitpython-ads1x15

COPY . /app

ENV PYTHONUNBUFFERED=1

# Set environment variables for Blinka
# -----------------------------
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV BLINKA_USE_LGPIO=1

# -----------------------------
# Run your main script

CMD ["python3", "system_convert.py"]
