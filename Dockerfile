# Use official Python slim image
FROM python:3.11-slim

# -----------------------------
# Install system dependencies
# -----------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
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
# Install lgpio from source
# -----------------------------
RUN git clone https://github.com/wiringPi/lgpio.git /tmp/lgpio && \
    cd /tmp/lgpio && \
    make && \
    make install && \
    rm -rf /tmp/lgpio

# -----------------------------
# Upgrade pip
# -----------------------------
RUN python3 -m pip install --upgrade pip

# -----------------------------
# Install Python packages (from requirements.txt)
# -----------------------------
COPY requirements.txt /app/
RUN python3 -m pip install -r /app/requirements.txt

# -----------------------------
# Set working directory and copy project
# -----------------------------
WORKDIR /app
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
