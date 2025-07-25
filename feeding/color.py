import cv2
import numpy as np
import time
from datetime import datetime, timedelta
from prometheus_client import start_http_server, Gauge, Summary
import schedule
import math

# ===== CUSTOMIZABLE PARAMETERS =====
FEEDING_TIMES = ["05:00", "20:00"]  # AM/PM feeding schedule
MONITOR_INTERVAL = 180  # minutes between checks
BASE_FEED_DURATION = 5  # seconds (median feeding time)
PUMP_PIN = 18  # GPIO pin

# Prometheus Metrics
COVERAGE = Gauge('algae_coverage', 'Current algae coverage percentage')
FEED_DURATION = Summary('algae_feeding_duration', 'Feeding duration seconds')
DAILY_TREND = Gauge('algae_daily_trend', 'Daily coverage trend coefficient')
# ===================================

class AlgaeSystem:
    def __init__(self):
        self.daily_readings = []
        self.setup_metrics()
        self.setup_hardware()
        
    def setup_metrics(self):
        start_http_server(8000)
        
    def setup_hardware(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(PUMP_PIN, GPIO.OUT)
            self.hardware_ready = True
        except:
            print("Running in simulation mode")
            self.hardware_ready = False

    def get_coverage(self):
        """Analyze current algae density"""
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if not ret: return None
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (30, 50, 50), (90, 255, 255))
        coverage = np.count_nonzero(mask) / mask.size * 100
        cap.release()
        
        # Store daily readings (resets at midnight)
        if not self.daily_readings or datetime.now().day != self.daily_readings[-1]['day']:
            self.daily_readings = []
        self.daily_readings.append({
            'time': datetime.now(),
            'day': datetime.now().day,
            'value': coverage
        })
        
        return coverage

    def calculate_daily_trend(self):
        """Calculate linear regression slope of today's readings"""
        if len(self.daily_readings) < 2: return 0
        
        x = [(r['time'] - self.daily_readings[0]['time']).total_seconds() for r in self.daily_readings]
        y = [r['value'] for r in self.daily_readings]
        
        # Linear regression
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi*yi for xi,yi in zip(x,y))
        sum_x2 = sum(xi**2 for xi in x)
        
        slope = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x**2)
        return slope * 3600  # Convert to % per hour

    def calculate_feeding_duration(self, current_coverage):
        """Dynamic duration based on daily trend and current density"""
        trend = self.calculate_daily_trend()
        DAILY_TREND.set(trend)
        
        # Formula: Base time adjusted by coverage and trend
        coverage_factor = (50 - current_coverage) / 50  # +1 at 0%, -1 at 100%
        trend_factor = 1 + math.tanh(trend)  # 0-2 range
        
        duration = BASE_FEED_DURATION * (1 + coverage_factor) * trend_factor
        return max(1, min(10, duration))  # Clamp 1-10 seconds

    def execute_feeding(self, duration):
        """Run pump for calculated duration"""
        if self.hardware_ready:
            import RPi.GPIO as GPIO
            GPIO.output(PUMP_PIN, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(PUMP_PIN, GPIO.LOW)
        FEED_DURATION.observe(duration)
        return duration

    def monitoring_cycle(self):
        """Regular density check without feeding"""
        coverage = self.get_coverage()
        if coverage is not None:
            COVERAGE.set(coverage)
            print(f"{datetime.now():%H:%M} - Coverage: {coverage:.1f}%")

    def feeding_cycle(self):
        """Scheduled feeding with dynamic duration"""
        coverage = self.get_coverage()
        if coverage is None: return
        
        duration = self.calculate_feeding_duration(coverage)
        actual_duration = self.execute_feeding(duration)
        
        print(f"{datetime.now():%H:%M} - Fed {actual_duration:.1f}s (Cov: {coverage:.1f}%)")

    def run(self):
        # Initial reading
        self.monitoring_cycle()
        
        # Schedule feedings
        for time_str in FEEDING_TIMES:
            schedule.every().day.at(time_str).do(self.feeding_cycle)
        
        # Schedule monitoring
        schedule.every(MONITOR_INTERVAL).minutes.do(self.monitoring_cycle)
        
        print("Algae monitoring system started")
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    system = AlgaeSystem()
    try:
        system.run()
    except KeyboardInterrupt:
        print("System stopped")
