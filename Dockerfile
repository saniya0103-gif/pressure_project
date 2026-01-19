# Use Python 3.12 slim for Pi 5 compatibility
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies for I2C & GPIO
RUN apt-get update && apt-get install -y \
    i2c-tools \
    libgpiod-dev \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Upgrade pip & install Python packages
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Force Blinka to Pi 4B to bypass Pi 5 microcontroller issue
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_4B
ENV BLINKA_FORCECHIP=BCM2711

# Run main script
CMD ["python3", "-u", "system_convert.py"]
