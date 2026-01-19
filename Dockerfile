# Use 3.12-bookworm for the best Pi 5 compatibility in 2026
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install dependencies required for the new Pi 5 GPIO architecture (RP1 chip)
RUN apt-get update && apt-get install -y \
    i2c-tools \
    libgpiod-dev \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip and install requirements
# Ensure your requirements.txt has 'rpi-lgpio' and 'lgpio', NOT 'RPi.GPIO'
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-u", "system_convert.py"]
