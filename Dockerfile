# Use Raspberry Pi Python image from balena
FROM balenalib/raspberrypi3-python:3.11

# Set working directory
WORKDIR /app

# Install system dependencies for I2C & build tools
RUN apt-get update && apt-get install -y \
    python3-smbus \
    i2c-tools \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command (convert app)
CMD ["python3", "system_convert.py"]