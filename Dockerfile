# Standalone OpenCV Shape Detection for Raspberry Pi
FROM python:3.9-slim-bullseye

# Install system dependencies for OpenCV and camera support
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
    libgtk-3-dev \
    libqt5gui5 \
    libqt5test5 \
    python3-pyqt5 \
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
COPY shape_detector_web.py .
COPY templates/ ./templates/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OPENCV_VIDEOIO_PRIORITY_V4L2=1
ENV QT_QPA_PLATFORM=xcb
ENV DISPLAY=:0

# Expose port for web dashboard
EXPOSE 5000

# Run the web application by default
CMD ["python", "shape_detector_web.py"]