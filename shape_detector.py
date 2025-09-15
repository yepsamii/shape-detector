import cv2
import numpy as np
import time
import os
import serial
from collections import deque

# Fix Qt plugin issues
os.environ['QT_QPA_PLATFORM'] = 'xcb'

# Initialize serial communication
try:
    arduino = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    time.sleep(2)
    print("Serial communication initialized successfully")
except Exception as e:
    print(f"Serial initialization error: {e}")
    exit(1)

# State management with proper timeouts for your Arduino
arduino_busy_until = 0

class DetectionStabilizer:
    def __init__(self, window_size=5, threshold=4):
        self.window_size = window_size
        self.threshold = threshold
        self.recent_detections = deque(maxlen=window_size)
        self.last_confirmed = None
        self.confirmation_time = 0

    def add_detection(self, detection):
        current_time = time.time()
        self.recent_detections.append(detection)

        # Don't confirm same shape too quickly
        if (self.last_confirmed == detection and
            current_time - self.confirmation_time < 6.0):
            return False, None

        # Check if we have enough consistent detections
        if len(self.recent_detections) >= self.threshold:
            recent_list = list(self.recent_detections)[-self.threshold:]
            if recent_list.count(detection) >= self.threshold:
                self.last_confirmed = detection
                self.confirmation_time = current_time
                return True, detection

        return False, None

    def reset(self):
        self.recent_detections.clear()

def send_to_arduino_simple(shape):
    """Send command with proper timeouts for your Arduino delays"""
    global arduino_busy_until

    try:
        print(f"\n=== Sending {shape} to Arduino ===")

        # Clear buffers
        arduino.reset_input_buffer()
        arduino.reset_output_buffer()

        # Send command
        command_map = {"triangle": 't', "circle": 'c', "square": 's'}
        command = command_map[shape]

        arduino.write(command.encode())
        arduino.flush()

        # Set appropriate timeout based on your Arduino timing
        if shape == "circle":
            processing_time = 10  # Circle: ~8s + 2s buffer
        else:  # triangle or square
            processing_time = 20  # Triangle/Square: ~18s + 2s buffer

        arduino_busy_until = time.time() + processing_time

        print(f"Command '{command}' sent. Arduino busy for {processing_time}s")
        return True

    except Exception as e:
        print(f"Send error: {e}")
        return False

def is_arduino_ready():
    """Check if Arduino is ready (with early completion detection)"""
    current_time = time.time()
    return current_time >= arduino_busy_until

def read_arduino_messages():
    """Read Arduino messages and detect early completion"""
    global arduino_busy_until

    try:
        while arduino.in_waiting > 0:
            msg = arduino.readline().decode(errors="ignore").strip()
            if msg:
                print(f"Arduino: {msg}")

                # Detect when Arduino completes task early
                if msg == "DONE":
                    print("✅ Arduino completed task!")
                    arduino_busy_until = 0  # Reset immediately when DONE received
                elif msg == "READY":
                    print("✅ Arduino ready for commands")
                    arduino_busy_until = 0  # Ensure ready state
                elif "detected - processing" in msg:
                    print("🤖 Arduino started processing...")
    except:
        pass

def classify_shape_optimized(contour):
    """Optimized shape classification for real-world conditions"""
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)

    # Basic filtering
    if perimeter == 0 or area < 2500:
        return "unknown"

    # Calculate properties
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = float(w) / h
    circularity = 4 * np.pi * area / (perimeter * perimeter)
    rect_area = w * h
    extent = float(area) / rect_area if rect_area > 0 else 0

    # Convex hull for better shape analysis
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity = float(area) / hull_area if hull_area > 0 else 0

    # Contour approximation - balanced approach
    epsilon = 0.02 * perimeter
    approx = cv2.approxPolyDP(contour, epsilon, True)
    vertices = len(approx)

    # Filter out very poor shapes
    if extent < 0.25 or solidity < 0.7:
        return "unknown"

    print(f"Shape Debug - V:{vertices}, AR:{aspect_ratio:.2f}, C:{circularity:.2f}, E:{extent:.2f}, S:{solidity:.2f}")

    # Multi-criteria classification

    # TRIANGLE Detection
    if vertices == 3:
        if 0.3 <= extent <= 0.85 and 0.4 <= aspect_ratio <= 2.0:
            return "triangle"

    # Additional triangle detection for missed cases
    if vertices <= 4 and circularity < 0.6 and solidity > 0.8:
        if 0.4 <= aspect_ratio <= 1.8 and extent < 0.7:
            return "triangle"

    # SQUARE Detection
    if vertices == 4:
        if 0.6 <= extent <= 0.95:
            if 0.75 <= aspect_ratio <= 1.35:  # Nearly square
                return "square"
            elif 0.4 <= aspect_ratio <= 2.5:  # Rectangle
                return "rectangle"

    # Additional square detection
    if 0.8 <= aspect_ratio <= 1.25 and extent > 0.7 and circularity < 0.8:
        return "square"

    # CIRCLE Detection
    if vertices >= 6 or circularity > 0.7:
        if circularity > 0.6 and solidity > 0.8:
            return "circle"

    # Fallback circle detection
    if circularity > 0.75:
        return "circle"

    # Final fallback based on aspect ratio and extent
    if vertices <= 4:
        if circularity < 0.5 and extent < 0.7:
            return "triangle"
        elif 0.7 <= aspect_ratio <= 1.3 and extent > 0.6:
            return "square"

    return "unknown"

def initialize_camera():
    """Initialize camera with multiple fallback options"""
    backends = [cv2.CAP_V4L2, cv2.CAP_FFMPEG, cv2.CAP_ANY]

    for backend in backends:
        for camera_id in [0, 1, 2]:
            try:
                cap = cv2.VideoCapture(camera_id, backend)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        # Configure camera
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_FPS, 15)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        print(f"Camera initialized: ID {camera_id}, Backend {backend}")
                        return cap
                    cap.release()
            except:
                continue
    return None

# Initialize camera
cap = initialize_camera()
if cap is None:
    print("Camera initialization failed")
    exit(1)

print("=== SYNC-OPTIMIZED SHAPE DETECTION WITH ARDUINO ===")

# Initialize stabilizer
stabilizer = DetectionStabilizer(window_size=5, threshold=4)
last_detection_time = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera frame read failed")
            break

        current_time = time.time()

        # Read Arduino messages (this can reset arduino_busy_until early)
        read_arduino_messages()

        # Check Arduino state
        arduino_ready = is_arduino_ready()

        if not arduino_ready:
            # Arduino processing - show status with proper timing
            remaining = arduino_busy_until - current_time
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 80), (0, 0, 200), -1)
            cv2.putText(frame, "ROBOT WORKING - CAMERA PAUSED", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Est. remaining: {remaining:.0f}s", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        else:
            # Arduino ready - detect shapes
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), (0, 200, 0), -1)
            cv2.putText(frame, "ARDUINO READY - DETECTING SHAPES", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Shape detection with timing control
            if current_time - last_detection_time > 1.0:

                # Enhanced preprocessing
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Adaptive preprocessing based on lighting
                blurred = cv2.GaussianBlur(gray, (7, 7), 0)

                # Try adaptive threshold first, fallback to Otsu
                thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY_INV, 11, 2)

                # If adaptive doesn't work well, use Otsu
                _, thresh_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

                # Combine both methods
                thresh = cv2.bitwise_or(thresh, thresh_otsu)

                # Morphological operations
                kernel = np.ones((4, 4), np.uint8)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

                # Find contours
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Filter contours by area
                valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 2500]

                if valid_contours:
                    # Process largest contour
                    largest_contour = max(valid_contours, key=cv2.contourArea)
                    shape = classify_shape_optimized(largest_contour)

                    if shape in ("circle", "triangle", "square"):
                        # Stabilize detection
                        is_stable, confirmed_shape = stabilizer.add_detection(shape)

                        if is_stable:
                            print(f"✓ CONFIRMED STABLE DETECTION: {confirmed_shape.upper()}")

                            # Visual feedback
                            cv2.drawContours(frame, [largest_contour], -1, (0, 255, 0), 3)

                            # Get contour center
                            M = cv2.moments(largest_contour)
                            if M["m00"] != 0:
                                cX = int(M["m10"] / M["m00"])
                                cY = int(M["m01"] / M["m00"])
                            else:
                                cX, cY = 0, 0

                            # Confirmation overlay
                            cv2.rectangle(frame, (cX-90, cY-50), (cX+90, cY+20), (0, 255, 0), -1)
                            cv2.putText(frame, f"CONFIRMED: {confirmed_shape.upper()}",
                                       (cX-85, cY-15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                            cv2.putText(frame, "SENDING TO ROBOT",
                                       (cX-85, cY+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

                            # Send to Arduino
                            if send_to_arduino_simple(confirmed_shape):
                                stabilizer.reset()
                                last_detection_time = current_time
                        else:
                            # Show detection in progress
                            cv2.putText(frame, f"Detecting: {shape}... (stabilizing)", (50, 100),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                            # Draw contour for feedback
                            cv2.drawContours(frame, [largest_contour], -1, (255, 255, 0), 2)
                    else:
                        # Unknown shape
                        cv2.putText(frame, f"Unknown shape detected", (50, 100),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                last_detection_time = current_time

        # Display frame
        cv2.imshow("Robot Shape Sorting System", frame)

        # Controls
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            arduino_busy_until = 0
            stabilizer.reset()
            print("🔄 MANUAL RESET: System reset to READY state")
        elif key == ord('q') or key == 27:  # 'q' or ESC
            print("🛑 Exit requested")
            break

except KeyboardInterrupt:
    print("🛑 Stopped by user (Ctrl+C)")
except Exception as e:
    print(f"❌ System error: {e}")
finally:
    # Cleanup
    print("🧹 Cleaning up...")
    if cap:
        cap.release()
    cv2.destroyAllWindows()
    if arduino:
        arduino.close()
    print("✅ Cleanup complete - System stopped safely")