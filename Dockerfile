# Use Raspberry Pi Python base image
FROM python:3.13-slim

# Install dependencies for I2C + SQLite
RUN apt-get update && \
    apt-get install -y python3-smbus i2c-tools libgpiod-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python code and requirements
COPY system_convert.py /app/
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Entry point
CMD ["python", "system_convert.py"]
