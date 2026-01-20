# -----------------------------
# Base image: official Python 3.11 Debian slim for ARM
# -----------------------------
FROM python:3.11-bullseye

# -----------------------------
# Install system dependencies
# -----------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        i2c-tools \
        python3-dev \
        gcc \
        build-essential \
        swig \
        liblgpio-dev \
        libgpiod2 \
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
# Copy requirements.txt (if you have one)
# -----------------------------
COPY requirements.txt /app/

# -----------------------------
# Install Python dependencies
# -----------------------------
RUN python3 -m pip install -r requirements.txt

# -----------------------------
# Copy your project files
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
# Default command to run your main script
# -----------------------------
CMD ["python3", "system_convert.py"]
