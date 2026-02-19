FROM arm64v8/python:3.11

WORKDIR /app

# Install Raspberry Pi system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    gcc \
    g++ \
    libgpiod2 \
    i2c-tools \
    python3-rpi.gpio \
    && rm -rf /var/lib/apt/lists/*

# Install pip packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

RUN mkdir -p /app/db

CMD ["python", "System_capture1.py"]
