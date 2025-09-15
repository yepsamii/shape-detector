# Raspberry Pi Local Setup Guide

## 📋 Prerequisites

### Hardware Requirements
- Raspberry Pi 3B+ or newer (recommended: Pi 4 with 4GB+ RAM)
- USB Camera connected to `/dev/video0`
- Arduino Nano connected via USB to `/dev/ttyUSB0`
- MicroSD card (minimum 16GB recommended)

### Software Requirements
- Raspberry Pi OS (Bullseye or newer)
- Python 3.7+ (usually pre-installed)
- Git (for cloning repository)

## 🌐 Web Dashboard vs OpenCV Window

This system supports **two modes**:

1. **Web Dashboard Mode** (`shape_detector_web.py`) - **RECOMMENDED**
   - Access via web browser at `http://pi-ip:5000`
   - Real-time camera feed in browser
   - Shape detection counts and statistics
   - Remote access from any device on network
   - Mobile-friendly interface

2. **OpenCV Window Mode** (`shape_detector.py`) - Direct display
   - Shows OpenCV window directly on Pi desktop
   - Requires monitor/VNC connection to Pi
   - Traditional computer vision display

## 🚀 Step-by-Step Local Installation

### Step 1: System Update and Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python development tools and camera utilities
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y v4l-utils
sudo apt install -y libopencv-dev python3-opencv

# Install system libraries for OpenCV
sudo apt install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev
sudo apt install -y libqtgui4 libqt4-test libqtcore4
```

### Step 2: Hardware Setup and Permissions

```bash
# Add user to dialout group for serial access
sudo usermod -aG dialout $USER

# Check available video devices
ls /dev/video*

# Check available serial ports
ls /dev/tty*

# Set permissions for serial port (replace with your port)
sudo chmod 666 /dev/ttyUSB0

# Test camera access
v4l2-ctl --list-devices

# Logout and login again to apply group changes
# Or run: newgrp dialout
```

### Step 3: Project Setup

```bash
# Clone or download the project
cd ~
git clone [your-repo-url] shape-detector
# OR if you have the files, create directory:
mkdir ~/shape-detector
cd ~/shape-detector

# Copy your project files here (shape_detector.py, requirements.txt, etc.)
```

### Step 4: Python Environment Setup

```bash
cd ~/shape-detector

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# If OpenCV fails to install via pip, use system package:
# pip install opencv-python==4.8.1.78 || echo "Using system OpenCV"
```

### Step 5: Configuration Verification

```bash
# Test camera access
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK:', cap.isOpened()); cap.release()"

# Test serial port access
python3 -c "import serial; s = serial.Serial('/dev/ttyUSB0', 9600, timeout=1); print('Serial OK'); s.close()"

# Test NumPy
python3 -c "import numpy as np; print('NumPy version:', np.__version__)"
```

### Step 6: Display Configuration (for OpenCV window)

```bash
# Enable X11 forwarding (if using SSH)
# Add this to ~/.bashrc or run before starting:
export DISPLAY=:0

# If running via SSH with X11 forwarding:
# ssh -X pi@[pi-ip-address]

# For direct Pi desktop, no additional setup needed
```

## 🔧 Running the Application

### Web Dashboard Mode (Recommended)

```bash
cd ~/shape-detector

# Activate virtual environment
source venv/bin/activate

# Run the web dashboard version
python3 shape_detector_web.py
```

**Access the dashboard:**
- Find your Pi's IP: `hostname -I`
- Open browser: `http://[PI-IP]:5000`
- Example: `http://192.168.1.100:5000`

### OpenCV Window Mode

```bash
cd ~/shape-detector

# Activate virtual environment
source venv/bin/activate

# Run the traditional OpenCV window version
python3 shape_detector.py
```

### Running as Background Service

```bash
# Create systemd service file for web dashboard
sudo nano /etc/systemd/system/shape-detector-web.service
```

Add this content:
```ini
[Unit]
Description=Shape Detector Web Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/shape-detector
Environment=PATH=/home/pi/shape-detector/venv/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/shape-detector/venv/bin/python shape_detector_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

For OpenCV window version (optional):
```ini
[Unit]
Description=Shape Detector OpenCV Window
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/shape-detector
Environment=PATH=/home/pi/shape-detector/venv/bin
Environment=DISPLAY=:0
ExecStart=/home/pi/shape-detector/venv/bin/python shape_detector.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start web dashboard service
sudo systemctl daemon-reload
sudo systemctl enable shape-detector-web.service
sudo systemctl start shape-detector-web.service

# Check service status
sudo systemctl status shape-detector-web.service

# View service logs
sudo journalctl -u shape-detector-web.service -f
```

## 🛠️ Configuration Customization

### Camera Settings

Edit `shape_detector.py` around line 199-203:
```python
# Camera configuration
CAMERA_INDEX = 0  # Change if using different camera
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Reduce for Pi 3
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Reduce for Pi 3
cap.set(cv2.CAP_PROP_FPS, 15)            # Reduce if struggling
```

### Serial Port Settings

Edit `shape_detector.py` around line 13:
```python
SERIAL_PORT = '/dev/ttyUSB0'  # Change to your Arduino port
BAUD_RATE = 9600              # Match Arduino baud rate
```

### Performance Optimization for Pi 3

```python
# Reduce resolution for better performance
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
cap.set(cv2.CAP_PROP_FPS, 10)

# In detection parameters (around line 113):
MIN_AREA = 1500  # Reduce minimum detection area
```

## 🔧 Troubleshooting

### Camera Issues

```bash
# Check camera permissions
ls -l /dev/video*

# Test with different camera indices
python3 -c "
for i in range(3):
    import cv2
    cap = cv2.VideoCapture(i)
    print(f'Camera {i}: {cap.isOpened()}')
    cap.release()
"

# Check camera with v4l2
v4l2-ctl --list-formats-ext
```

### Serial Port Issues

```bash
# Check available ports
dmesg | grep tty

# Check permissions
ls -l /dev/ttyUSB* /dev/ttyACM*

# Test Arduino connection
screen /dev/ttyUSB0 9600
# Press Ctrl+A then K to exit

# Monitor serial communication
sudo minicom -D /dev/ttyUSB0 -b 9600
```

### OpenCV Display Issues

```bash
# For SSH X11 forwarding
echo $DISPLAY
xauth list

# Install X11 libraries if missing
sudo apt install -y libx11-6 libxext6 libxrender1 libxtst6 libxi6

# Test X11 display
xclock  # Should show a clock window
```

### Memory Issues (Pi 3)

```bash
# Check memory usage
free -h

# Increase GPU memory split
sudo raspi-config
# Advanced Options > Memory Split > Set to 128 or 256

# Monitor system resources while running
htop
```

### Python Dependencies Issues

```bash
# If OpenCV installation fails
sudo apt install -y python3-opencv
pip install --no-deps opencv-python

# If NumPy issues
sudo apt install -y python3-numpy
pip install --upgrade numpy

# Alternative: use system packages
pip install --system-site-packages opencv-python pyserial numpy
```

## 📊 Monitoring and Logging

### View Application Logs

```bash
# If running directly
python3 shape_detector.py 2>&1 | tee shape_detector.log

# If running as service
sudo journalctl -u shape-detector.service -f --no-pager

# Check system resources
htop
iotop  # Install with: sudo apt install iotop
```

### Performance Monitoring

```bash
# Monitor CPU temperature
vcgencmd measure_temp

# Monitor GPU memory
vcgencmd get_mem gpu

# Check for throttling
vcgencmd get_throttled
```

## 🚀 Auto-Start Configuration

### Desktop Auto-Start

```bash
# Create autostart directory
mkdir -p ~/.config/autostart

# Create desktop entry
cat > ~/.config/autostart/shape-detector.desktop << EOF
[Desktop Entry]
Type=Application
Name=Shape Detector
Exec=/home/pi/shape-detector/venv/bin/python /home/pi/shape-detector/shape_detector.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

### Boot Configuration

Add to `/etc/rc.local` (before `exit 0`):
```bash
# Start shape detector
sudo -u pi /home/pi/shape-detector/venv/bin/python /home/pi/shape-detector/shape_detector.py &
```

## 🔄 Updating the Application

```bash
cd ~/shape-detector

# Stop the service if running
sudo systemctl stop shape-detector.service

# Activate environment
source venv/bin/activate

# Update code (if using git)
git pull

# Update dependencies if needed
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl start shape-detector.service
```

## 🌐 Web Dashboard Features

### Dashboard Access
- **URL**: `http://[PI-IP]:5000`
- **Mobile friendly**: Works on phones/tablets
- **Real-time updates**: Live camera feed and detection counts
- **No software installation**: Access from any browser

### Dashboard Interface
- **Live Camera Feed**: Real-time video stream with detection overlays
- **Shape Counts**: Circle, square, triangle detection counters
- **Current Detection**: Shows currently detected shape
- **Interactive Chart**: Visual representation of shape distribution
- **Reset Button**: Clear all counts and reset system state

### Dashboard Controls
- **Reset Counts**: Click button to reset all shape counters
- **Automatic Updates**: Real-time updates via WebSocket connection
- **Connection Status**: Visual indicator showing system connectivity

## 📝 Control Commands

### OpenCV Window Mode Controls
- **'r' key**: Reset Arduino state and detection stabilizer
- **'q' or ESC**: Exit application
- **Ctrl+C**: Force exit (in terminal)

### Web Dashboard Controls
- **Browser Reset Button**: Reset all counts and Arduino state
- **Close browser**: Application continues running in background
- **Ctrl+C in terminal**: Stop web server

## 💡 Tips for Optimal Performance

1. **Use a fast MicroSD card** (Class 10 or better)
2. **Ensure adequate power supply** (official Pi power adapter recommended)
3. **Keep the Pi cool** (heatsinks or fan recommended)
4. **Close unnecessary services** to free up resources
5. **Position camera properly** for consistent lighting
6. **Test Arduino communication** before running detection
7. **Monitor system temperature** during extended use

This setup provides a robust, local installation that doesn't require Docker while maintaining all the functionality of the shape detection system.