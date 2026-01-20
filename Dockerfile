FROM python:3.11-slim-bullseye

WORKDIR /app

# System dependencies for I2C and GPIO
RUN apt-get update && apt-get install -y --no-install-recommends \
    i2c-tools \
    python3-dev \
    gcc \
    libgpiod2 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install Python libraries from requirements.txt
COPY requirements.txt /app/
RUN python3 -m pip install -r requirements.txt

# Copy project files
COPY . /app

# Blinka environment variables
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_5
ENV BLINKA_FORCECHIP=BCM2712
ENV BLINKA_USE_LGPIO=1
ENV PYTHONUNBUFFERED=1

# Run the main script
CMD ["python3", "system_convert.py"]
