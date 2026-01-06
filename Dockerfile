# Use Python 3.13 slim image
FROM python:3.13-slim

# Avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

#Install system dependencies and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    make \
    gcc \
    swig \
    cmake \
    libgpiod-dev \
    python3-smbus \
    i2c-tools \
    curl \
    unzip \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

#Clone and build lgpio library
#RUN git clone https://github.com/derekmolloy/lgpio.git /tmp/lgpio && \
 #   cd /tmp/lgpio && \
  #  make && make install && \
    # rm -rf /tmp/lgpio
#Set working directory
WORKDIR /app

# Clone your public pressure_project repository
RUN git clone https://github.com/saniya0103-gif/pressure_project.git /app

#Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

#Command to run your Python script
CMD ["python", "/app/system_convert.py"]
