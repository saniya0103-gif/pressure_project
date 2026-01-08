FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install required system packages for I2C + lgpio + building Python extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-smbus \
    i2c-tools \
    libgpiod-dev \
    liblgpio-dev \
    swig \
    python3-dev \
    build-essential \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir lgpio adafruit-blinka

# Set working directory
WORKDIR /app

# Copy and install project Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command to run your script
CMD ["python", "system_convert.py"]
# Alternative command to run the upload script
CMD ["python", "system_upload.py"]
