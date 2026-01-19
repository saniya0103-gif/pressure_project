FROM python:3.11-bookworm

WORKDIR /app

# Install system dependencies for I2C + lgpio
RUN apt-get update && apt-get install -y \
    i2c-tools \
    python3-lgpio \
    libgpiod2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

CMD ["python3", "system_convert.py"]
