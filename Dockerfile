FROM python:3.11-bookworm

WORKDIR /app

# Install only system dependencies
RUN apt-get update && apt-get install -y \
    i2c-tools \
    libgpiod2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install lgpio via pip
RUN pip install --no-cache-dir lgpio==0.2.2.0

# Install the rest of Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

CMD ["python3", "system_convert.py"]
