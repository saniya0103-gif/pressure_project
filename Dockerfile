# Use Python 3.13 slim
FROM python:3.13-slim

# Install build tools + I2C dependencies
RUN apt-get update && \
    apt-get install -y python3-smbus i2c-tools libgpiod-dev gcc lgpio && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy your code
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run only system_convert.py
CMD ["python", "system_convert.py"]
