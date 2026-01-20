# -----------------------------
# Base image
# -----------------------------
FROM python:3.11-bullseye

# -----------------------------
# Install system dependencies
# -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    i2c-tools \
    build-essential \
    python3-dev \
    gcc \
    swig \
    libgpiod2 \
    python3-pip \
    git \
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
# Copy requirements and install
# -----------------------------
COPY requirements.txt /app/
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
