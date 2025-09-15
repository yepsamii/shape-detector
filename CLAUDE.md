# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a standalone real-time shape detection system built for Raspberry Pi that detects shapes (circles, squares, triangles) using OpenCV computer vision and communicates with an Arduino via serial. The system features a direct OpenCV display window with advanced shape classification and detection stabilization.

## Architecture

### Core Detection Engine (`shape_detector.py`)
- **Advanced Shape Classification**: Multi-criteria shape analysis using contour properties, circularity, aspect ratio, extent, and solidity
- **Detection Stabilization**: Requires 4 consistent detections within a 5-frame window to confirm shape identification
- **Camera Processing**: Robust camera initialization with multiple backend fallbacks (V4L2, FFMPEG, CAP_ANY)
- **Serial Communication**: Sends shape codes ('c', 's', 't') to Arduino with intelligent timeout management
- **Arduino State Management**: Tracks Arduino processing status with early completion detection via "DONE" messages
- **Enhanced Preprocessing**: Combines adaptive thresholding and Otsu's method with morphological operations

### Hardware Integration
- **Camera Interface**: USB camera via `/dev/video0` with multiple backend support
- **Arduino Communication**: Serial communication via `/dev/ttyUSB0` at 9600 baud with buffer management
- **Docker Deployment**: Containerized with X11 forwarding for OpenCV display window

## Development Commands

### Docker Operations (Primary Method)
```bash
# Build and run the system (requires X11 display)
export DISPLAY=:0
xhost +local:docker
docker-compose build
docker-compose up

# View real-time logs
docker-compose logs -f

# Stop the system
docker-compose down

# Rebuild after code changes
docker-compose build --no-cache
```

### Direct Python Execution (Development)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application (requires camera and Arduino connected)
python shape_detector.py
```

### Hardware Configuration
```bash
# Check available video devices
ls /dev/video*

# Check available serial ports
ls /dev/tty*

# Test camera access
v4l2-ctl --list-devices
```

## Configuration

### Camera Settings (`shape_detector.py:199-203`)
- Resolution: 640x480 (configurable in `initialize_camera()`)
- Frame rate: 15 FPS
- Buffer size: 1 (low latency)
- Multiple backend fallback support

### Serial Settings (`shape_detector.py:13`)
- `SERIAL_PORT`: Arduino connection (default: `/dev/ttyUSB0`)
- `BAUD_RATE`: Communication speed (9600)
- Timeout: 1 second

### Detection Parameters (`shape_detector.py:113-185`)
- **Minimum area threshold**: 2500 pixels
- **Detection stabilization**: 4 confirmations in 5-frame window
- **Shape confirmation cooldown**: 6 seconds between same shape detections
- **Advanced classification**: Multi-criteria analysis with fallback methods

### Arduino Timing (`shape_detector.py:72-76`)
- **Circle processing**: 10 seconds (8s + 2s buffer)
- **Triangle/Square processing**: 20 seconds (18s + 2s buffer)
- **Early completion**: Monitors for "DONE" messages to reset timing

## Key Technical Details

### Advanced Shape Detection Algorithm
1. **Preprocessing**: Grayscale → Gaussian blur → Adaptive + Otsu thresholding
2. **Morphological Operations**: Closing and opening to clean noise
3. **Contour Analysis**: External contours with area filtering (>2500 pixels)
4. **Multi-Criteria Classification**:
   - Vertex counting via contour approximation
   - Circularity calculation (4πA/P²)
   - Aspect ratio analysis
   - Extent and solidity measurements
5. **Detection Stabilization**: Requires multiple consistent detections
6. **Visual Feedback**: Real-time status overlays and shape confirmation

### Arduino Communication Protocol
- **Shape codes**: 'c' (circle), 's' (square), 't' (triangle)
- **Response monitoring**: Listens for "DONE", "READY", and processing messages
- **Buffer management**: Input/output buffer clearing before transmission
- **Timeout handling**: Shape-specific processing times with early completion detection

### User Controls
- **'r' key**: Manual reset of Arduino state and detection stabilizer
- **'q' or ESC**: Exit application
- **Real-time display**: Shows Arduino status, detection progress, and shape confirmations

### Docker Configuration
- **X11 forwarding**: Enables OpenCV display window in container
- **Device passthrough**: Camera (`/dev/video0`) and Arduino (`/dev/ttyUSB0`)
- **Privileged mode**: Required for hardware access
- **Environment variables**: Display configuration and Qt platform settings

## Troubleshooting

### Common Issues
- **Camera not detected**: System tries multiple camera IDs (0,1,2) and backends automatically
- **Serial connection failed**: Application exits immediately - check Arduino connection and port
- **Display issues**: Ensure X11 forwarding is enabled (`xhost +local:docker`)
- **Permission denied**: Ensure user is in `dialout` group for serial access
- **Qt platform issues**: System sets `QT_QPA_PLATFORM=xcb` automatically

### Development Notes
- **Graceful degradation**: System handles missing camera gracefully but requires Arduino connection
- **Debug output**: Extensive console logging for shape analysis and Arduino communication
- **Visual feedback**: Real-time status indicators show Arduino state and detection progress
- **Robust initialization**: Multiple fallback options for camera and backend selection
- **Performance optimization**: 1-second minimum detection interval to prevent Arduino overload