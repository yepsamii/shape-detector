# Shape Detection System - Docker Setup Documentation

## 📋 Prerequisites

### Hardware Requirements
- Raspberry Pi 3B+ or newer (recommended: Pi 4 with 4GB+ RAM)
- USB Camera connected to Raspberry Pi
- Arduino Nano connected via USB
- Sufficient SD card space (minimum 8GB recommended)

### Software Requirements
- Raspberry Pi OS (Bullseye or newer)
- Docker and Docker Compose installed
- Git (for cloning repository)

## 🚀 Step-by-Step Installation

### Step 1: Install Docker on Raspberry Pi

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group (avoid using sudo)
sudo usermod -aG docker $USER

# Logout and login again or run:
newgrp docker

# Verify Docker installation
docker --version
```

### Step 2: Install Docker Compose

```bash
# Install Python pip
sudo apt-get install -y python3-pip

# Install Docker Compose
sudo pip3 install docker-compose

# Verify installation
docker-compose --version
```

### Step 3: Project Setup

```bash
# Create project directory
mkdir ~/shape_detector_system
cd ~/shape_detector_system

# Create project structure
mkdir templates logs
```

### Step 4: Create Project Files

Create the following files in your project directory:

1. **shape_detector.py** - Main Python application (provided above)
2. **templates/index.html** - Web dashboard (provided above)
3. **requirements.txt** - Python dependencies (provided above)
4. **Dockerfile** - Docker configuration (provided above)
5. **docker-compose.yml** - Docker Compose configuration (provided above)

### Step 5: Configure Serial Port

```bash
# List available serial ports
ls /dev/tty*

# Find your Arduino (usually /dev/ttyUSB0 or /dev/ttyACM0)
# Update SERIAL_PORT in shape_detector.py if different

# Grant permission to serial port
sudo chmod 666 /dev/ttyUSB0  # Replace with your port
```

### Step 6: Configure Camera

```bash
# List available video devices
ls /dev/video*

# Test camera (optional)
sudo apt-get install -y v4l-utils
v4l2-ctl --list-devices

# If camera is not /dev/video0, update CAMERA_INDEX in shape_detector.py
```

## 🔨 Building and Running with Docker

### Option 1: Using Docker Compose (Recommended)

```bash
# Build the Docker image
docker-compose build

# Run the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Option 2: Using Docker Commands

```bash
# Build the image
docker build -t shape-detector:latest .

# Run the container
docker run -d \
  --name shape_detector \
  -p 5000:5000 \
  --device /dev/video0:/dev/video0 \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  --privileged \
  --restart unless-stopped \
  shape-detector:latest

# View logs
docker logs -f shape_detector

# Stop the container
docker stop shape_detector
docker rm shape_detector
```

## 🌐 Accessing the Dashboard

1. Find your Raspberry Pi's IP address:
```bash
hostname -I
```

2. Open a web browser and navigate to:
```
http://[YOUR_PI_IP]:5000
```

Example: `http://192.168.1.100:5000`

## 🔧 Troubleshooting

### Camera Issues

```bash
# Check if camera is detected
docker exec shape_detector ls /dev/video*

# Test camera inside container
docker exec -it shape_detector python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### Serial Port Issues

```bash
# Check serial port permissions
ls -l /dev/ttyUSB*

# Test serial inside container
docker exec shape_detector ls /dev/tty*

# Monitor serial communication
docker exec shape_detector cat /dev/ttyUSB0
```

### Container Not Starting

```bash
# Check container logs
docker logs shape_detector

# Check if port 5000 is already in use
sudo netstat -tulpn | grep 5000

# Inspect container
docker inspect shape_detector
```

## 🛠️ Configuration Adjustments

### Modify Camera Settings

Edit `shape_detector.py` and rebuild:
```python
# Camera configuration
CAMERA_INDEX = 0  # Change if using different camera
FRAME_WIDTH = 640  # Reduce for better performance
FRAME_HEIGHT = 480
FPS = 15  # Reduce if Pi is struggling
```

### Modify Serial Port

Edit `shape_detector.py`:
```python
SERIAL_PORT = '/dev/ttyUSB0'  # Change to your Arduino port
BAUD_RATE = 9600  # Match Arduino baud rate
```

### Performance Optimization

For Raspberry Pi 3 or lower specs:
```python
# Reduce resolution
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
FPS = 10

# Adjust JPEG quality in generate_frames()
cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
```

## 📊 Monitoring

### View Real-time Logs

```bash
# All logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Save logs to file
docker-compose logs