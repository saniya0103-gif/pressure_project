FROM ghcr.io/adafruit/raspberry-pi-python:3.11

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "system_convert.py"]
