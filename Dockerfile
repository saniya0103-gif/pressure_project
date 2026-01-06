# Use Python 3.13 slim
FROM python:3.13-slim

# Install build tools + I2C dependencies + SWIG + git + cmake + make + ca-certificates
RUN apt-get update && \
    apt-get install -y python3-smbus i2c-tools libgpiod-dev gcc swig git cmake make ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Build and install lgpio library from source
# Build and install lgpio library from source (download zip)
RUN apt-get update && apt-get install -y unzip && \
    curl -L -o /tmp/lgpio.zip https://github.com/derekmolloy/lgpio/archive/refs/heads/master.zip && \
    unzip /tmp/lgpio.zip -d /tmp/ && \
    cd /tmp/lgpio-master && \
    make && make install && \
    rm -rf /tmp/lgpio* 

# Set working directory
WORKDIR /app

# Copy your project
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run only system_convert.py
CMD ["python", "system_convert.py"]
