FROM python:3.13-slim

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install Python packages using python3
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . .

# Default command (for uploader)
CMD ["python3", "system_upload.py"]
