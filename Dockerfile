FROM python:3.11-bookworm

WORKDIR /app

# Install ONLY required system dependency for I2C
RUN apt-get update && apt-get install -y \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Upgrade pip and install python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command
CMD ["python3", "system_convert.py"]
