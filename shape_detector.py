#!/usr/bin/env python3
import cv2
import numpy as np
import serial
import time
import threading
import base64
from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import logging
from queue import Queue
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables
shape_counts = {'circle': 0, 'square': 0, 'triangle': 0}
current_shape = 'none'
frame_queue = Queue(maxsize=2)
arduino_serial = None
camera = None
detection_active = True

# Serial configuration
SERIAL_PORT = '/dev/ttyUSB0'  # Adjust based on your Arduino connection
BAUD_RATE = 9600

# Camera configuration (optimized for Pi)
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 15

def init_serial():
    """Initialize serial connection with Arduino"""
    global arduino_serial
    try:
        arduino_serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino to initialize
        logger.info(f"Serial connected on {SERIAL_PORT}")
        return True
    except Exception as e:
        logger.error(f"Serial connection failed: {e}")
        return False

def init_camera():
    """Initialize camera with optimized settings"""
    global camera
    try:
        camera = cv2.VideoCapture(CAMERA_INDEX)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        camera.set(cv2.CAP_PROP_FPS, FPS)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for lower latency
        logger.info("Camera initialized")
        return True
    except Exception as e:
        logger.error(f"Camera initialization failed: {e}")
        return False

def detect_shape(contour):
    """Detect shape from contour"""
    epsilon = 0.04 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    vertices = len(approx)
    
    if vertices == 3:
        return 'triangle', 't'
    elif vertices == 4:
        # Check if square or rectangle
        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h
        if 0.85 <= aspect_ratio <= 1.15:
            return 'square', 's'
    elif vertices > 4:
        # Check for circle
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if perimeter > 0:
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            if circularity > 0.7:
                return 'circle', 'c'
    
    return None, None

def process_frame(frame):
    """Process frame for shape detection"""
    global current_shape
    
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    detected_shape = None
    shape_char = None
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1000:  # Minimum area threshold
            shape_name, shape_code = detect_shape(contour)
            if shape_name:
                detected_shape = shape_name
                shape_char = shape_code
                
                # Draw contour and label
                cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cv2.putText(frame, shape_name, (cx - 30, cy), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                break
    
    # Update current shape
    if detected_shape != current_shape:
        current_shape = detected_shape if detected_shape else 'none'
        socketio.emit('shape_update', {'shape': current_shape})
    
    return frame, shape_char

def detection_loop():
    """Main detection loop"""
    global detection_active, shape_counts
    
    while detection_active:
        try:
            if camera is None:
                time.sleep(1)
                continue
                
            ret, frame = camera.read()
            if not ret:
                logger.warning("Failed to grab frame")
                time.sleep(0.1)
                continue
            
            # Process frame
            processed_frame, shape_char = process_frame(frame)
            
            # Send to Arduino if shape detected
            if shape_char and arduino_serial:
                try:
                    arduino_serial.write(shape_char.encode())
                    logger.info(f"Sent '{shape_char}' to Arduino")
                    
                    # Wait for Arduino response
                    start_time = time.time()
                    while time.time() - start_time < 10:  # 10 second timeout
                        if arduino_serial.in_waiting:
                            response = arduino_serial.readline().decode().strip()
                            if response == 'done':
                                # Update counts
                                shape_name = {'c': 'circle', 's': 'square', 't': 'triangle'}[shape_char]
                                shape_counts[shape_name] += 1
                                
                                # Emit update to dashboard
                                socketio.emit('count_update', shape_counts)
                                logger.info(f"Updated {shape_name} count to {shape_counts[shape_name]}")
                                break
                        time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Serial communication error: {e}")
            
            # Put frame in queue for streaming
            if not frame_queue.full():
                frame_queue.put(processed_frame)
            
            time.sleep(0.05)  # Small delay to prevent CPU overload
            
        except Exception as e:
            logger.error(f"Detection loop error: {e}")
            time.sleep(1)

def generate_frames():
    """Generate frames for MJPEG streaming"""
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            time.sleep(0.03)

@app.route('/')
def index():
    """Serve main dashboard page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected")
    emit('initial_data', {
        'counts': shape_counts,
        'current_shape': current_shape
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected")

@socketio.on('reset_counts')
def handle_reset():
    """Reset shape counts"""
    global shape_counts
    shape_counts = {'circle': 0, 'square': 0, 'triangle': 0}
    emit('count_update', shape_counts, broadcast=True)
    logger.info("Counts reset")

def cleanup():
    """Cleanup resources"""
    global detection_active, camera, arduino_serial
    
    detection_active = False
    
    if camera:
        camera.release()
    
    if arduino_serial:
        arduino_serial.close()
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        # Initialize components
        if not init_camera():
            logger.error("Camera initialization failed - continuing anyway")
        
        if not init_serial():
            logger.error("Serial initialization failed - continuing anyway")
        
        # Start detection thread
        detection_thread = threading.Thread(target=detection_loop, daemon=True)
        detection_thread.start()
        
        # Start Flask app
        logger.info("Starting web server on http://0.0.0.0:5000")
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        cleanup()