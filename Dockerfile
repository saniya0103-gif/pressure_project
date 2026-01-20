# -----------------------------
# Dockerfile for Raspberry Pi 5
# -----------------------------

FROM python:3.11-bullseye

# -----------------------------
# Install system dependencies
# -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    python3-dev \
    gcc \
    swig \
    libgpiod2 \
    i2c-tools \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Set working directory
# -----------------------------
WORKDIR /app

# -----------------------------
# Clone and build lgpio C library
# -----------------------------
RUN git clone https://github.com/wiringPi/lgpio.git /tmp/lgpio && \
    cd /tmp/lgpio && \
    make && make install && \
    rm -rf /tmp/lgpio

# -----------------------------
# Upgrade pip and install Python libraries
# -----------------------------
COPY requirements.txt /app/
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

# -----------------------------
# Copy project files
# -----------------------------
COPY . /app

# -----------------------------
# Blinka environment variables
# -----------------------------
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV BLINKA_USE_LGPIO=1
ENV PYTHONUNBUFFERED=1

# -----------------------------
# Run main script
# -----------------------------
CMD ["python3", "system_convert.py"]
