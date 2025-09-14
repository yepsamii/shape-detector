# Multi-stage build for Raspberry Pi optimization
FROM python:3.9-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-opencv \
    libopencv-dev \
    libatlas-base-dev \
    libjpeg-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    v4l-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY shape_detector.py .
COPY templates/ ./templates/

# Create necessary directories
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OPENCV_VIDEOIO_PRIORITY_V4L2=1

# Expose port for Flask
EXPOSE 5000

# Run the application
CMD ["python", "shape_detector.py"]