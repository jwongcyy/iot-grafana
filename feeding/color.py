import cv2
import numpy as np
import time
from datetime import datetime
import RPi.GPIO as GPIO  # For Raspberry Pi (comment out if using Arduino)

# Configuration
LOWER_GREEN = (30, 50, 50)    # HSV lower bound for algae
UPPER_GREEN = (90, 255, 255)  # HSV upper bound
DISPENSE_TIMES = ["04:00", "22:00"]  # AM/PM dispensing schedule
PUMP_PIN = 18                  # GPIO pin for pump control
LOG_FILE = "algae_log.csv"

# Initialize GPIO (Raspberry Pi)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_PIN, GPIO.OUT)
GPIO.output(PUMP_PIN, GPIO.LOW)

def analyze_algae(frame):
    """Analyzes algae coverage from a frame."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_GREEN, UPPER_GREEN)
    coverage = np.count_nonzero(mask) / mask.size * 100
    return coverage

def control_pump(state):
    """Controls the pump (ON/OFF)."""
    GPIO.output(PUMP_PIN, state)
    print(f"Pump {'ON' if state else 'OFF'}")

def log_data(coverage, action):
    """Logs data to a CSV file."""
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp},{coverage:.2f},{action}\n")

def check_dispense_time():
    """Checks if current time matches dispensing schedule."""
    current_time = datetime.now().strftime("%H:%M")
    return current_time in DISPENSE_TIMES

def main():
    cap = cv2.VideoCapture(0)  # Use camera index (0 for default)
    last_dispense_day = -1

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Analyze algae coverage
            coverage = analyze_algae(frame)
            current_day = datetime.now().day

            # Check if it's a new day and dispensing time
            if current_day != last_dispense_day and check_dispense_time():
                if coverage < 30:  # Too sparse
                    control_pump(GPIO.HIGH)
                    time.sleep(5)  # Dispense for 5 seconds
                    control_pump(GPIO.LOW)
                    log_data(coverage, "DISPENSED")
                last_dispense_day = current_day

            # Display live feed
            cv2.putText(frame, f"Coverage: {coverage:.2f}%", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Algae Monitor", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        GPIO.cleanup()

if __name__ == "__main__":
    # Initialize log file header
    with open(LOG_FILE, "w") as f:
        f.write("Timestamp,Coverage(%),Action\n")
    main()
