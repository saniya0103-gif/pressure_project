FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    i2c-tools \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip

# Install ONLY required Python libs
RUN pip install \
    smbus2 \
    paho-mqtt \
    requests \
    pytz \
    AWSIoTPythonSDK

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "system_convert.py"]
