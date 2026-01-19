FROM python:3.11-slim-bookworm

WORKDIR /app

# System dependencies for Pi 5 GPIO + I2C
RUN apt-get update && apt-get install -y \
    i2c-tools \
    libgpiod-dev \
    libgpiod2 \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Python libraries (NO RPi.GPIO)
RUN pip install --no-cache-dir \
    adafruit-blinka \
    adafruit-circuitpython-ads1x15 \
    lgpio \
    smbus2 \
    paho-mqtt \
    requests \
    pytz \
    AWSIoTPythonSDK

COPY . .

ENV BLINKA_FORCEBOARD=RASPBERRY_PI_4B
ENV BLINKA_FORCECHIP=BCM2711
ENV BLINKA_USE_LGPIO=1
ENV PYTHONUNBUFFERED=1

CMD ["python3", "-u", "system_convert.py"]
