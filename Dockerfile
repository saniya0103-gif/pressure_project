FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system packages (this fixes your error)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-lgpio \
    python3-smbus \
    i2c-tools \
    libgpiod-dev \
    build-essential \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "system_convert.py"]
