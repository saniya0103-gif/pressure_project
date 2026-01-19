FROM python:3.9-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y \
    i2c-tools \
    libgpiod2 \
    python3-rpi.gpio \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-u", "system_convert.py"]
