# Use stable Python version
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python3", "system_upload.py"]
