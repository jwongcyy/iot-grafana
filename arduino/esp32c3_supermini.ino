

#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_NeoPixel.h>

// GPIO where DS18B20 is connected
const int oneWireBus = 4;

// WS2812 LED on ESP32 C3 Super Mini
#define LED_PIN     8
#define LED_COUNT   1
Adafruit_NeoPixel pixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// Setup oneWire instance
OneWire oneWire(oneWireBus);
DallasTemperature sensors(&oneWire);

// Color definitions
uint32_t GREEN = pixel.Color(0, 255, 0);
uint32_t BLUE = pixel.Color(0, 0, 255);
uint32_t RED = pixel.Color(255, 0, 0);
uint32_t YELLOW = pixel.Color(255, 255, 0);
uint32_t PURPLE = pixel.Color(255, 0, 255);
uint32_t CYAN = pixel.Color(0, 255, 255);
uint32_t ORANGE = pixel.Color(255, 165, 0);
uint32_t WHITE = pixel.Color(255, 255, 255);
uint32_t OFF = pixel.Color(0, 0, 0);

// Timing variables
unsigned long startTime = 0;
unsigned long lastSensorCheck = 0;
unsigned long lastTemperatureRead = 0;
const unsigned long SENSOR_CHECK_INTERVAL = 30000;    // 30 seconds
const unsigned long TEMPERATURE_READ_INTERVAL = 3600000; // 1 hour

void setup() {
  Serial.begin(115200);
  
  // Initialize NeoPixel
  pixel.begin();
  pixel.setBrightness(30); // 30% brightness
  pixel.clear();
  pixel.show();
  
  // Initialize DS18B20
  sensors.begin();

  startTime = millis();
  
  // Startup blink
  blinkColor(BLUE, 2, 200);
  
  printTime("System started");
  
  // Check sensor immediately
  checkSensor();
  
  // Take FIRST READING immediately after startup
  readTemperature();
  lastTemperatureRead = millis(); // Set timer for next reading
}

void loop() {
  unsigned long currentTime = millis();
  
  // Periodically check sensor connection
  if (currentTime - lastSensorCheck >= SENSOR_CHECK_INTERVAL) {
    checkSensor();
    lastSensorCheck = currentTime;
  }
  
  // Read temperature hourly
  if (currentTime - lastTemperatureRead >= TEMPERATURE_READ_INTERVAL) {
    readTemperature();
    lastTemperatureRead = currentTime;
  }
  
  // Slow heartbeat when connected
  static unsigned long lastHeartbeat = 0;
  if (currentTime - lastHeartbeat >= 10000) { // Every 10 seconds
    lastHeartbeat = currentTime;
    if (sensors.getDeviceCount() > 0) {
      // Quick green blink for heartbeat
      pixel.setPixelColor(0, GREEN);
      pixel.show();
      delay(50);
      pixel.clear();
      pixel.show();
    }
  }
  
  delay(100);
}

void checkSensor() {
  int deviceCount = sensors.getDeviceCount();
  
  printTime("Checking sensor");
  
  if (deviceCount > 0) {
    // Sensor connected - single green blink
    blinkColor(GREEN, 1, 100);
    Serial.print("  Sensor status: CONNECTED (");
    Serial.print(deviceCount);
    Serial.println(" devices)");
  } else {
    // No sensor - red blink
    blinkColor(RED, 2, 200);
    Serial.println("  Sensor status: DISCONNECTED");
  }
}

void readTemperature() {
  // Skip if no sensor
  if (sensors.getDeviceCount() == 0) {
    printTime("Skipping temperature read - no sensor");
    return;
  }
  
  printTime("Reading temperature");
  
  // Blue during reading
  pixel.setPixelColor(0, BLUE);
  pixel.show();
  
  sensors.requestTemperatures();
  float temperatureC = sensors.getTempCByIndex(0);
  
  // Clear LED
  pixel.clear();
  pixel.show();
  
  if (temperatureC == DEVICE_DISCONNECTED_C) {
    Serial.println("  Error reading temperature");
    blinkColor(RED, 3, 150);
  } else {
    Serial.print("  Temperature: ");
    Serial.print(temperatureC);
    Serial.println("°C");
    
    // Quick success blink
    blinkColor(GREEN, 1, 50);
  }
}

void blinkColor(uint32_t color, int count, int speed) {
  for (int i = 0; i < count; i++) {
    pixel.setPixelColor(0, color);
    pixel.show();
    delay(speed);
    pixel.clear();
    pixel.show();
    if (i < count - 1) delay(speed);
  }
}

void printTime(const char* message) {
  unsigned long currentTime = millis();
  unsigned long uptime = currentTime - startTime;
  
  unsigned long seconds = uptime / 1000;
  unsigned long minutes = seconds / 60;
  unsigned long hours = minutes / 60;
  
  seconds %= 60;
  minutes %= 60;
  hours %= 24;
  
  // Print timestamp [HH:MM:SS]
  Serial.print("[");
  if (hours < 10) Serial.print("0");
  Serial.print(hours);
  Serial.print(":");
  if (minutes < 10) Serial.print("0");
  Serial.print(minutes);
  Serial.print(":");
  if (seconds < 10) Serial.print("0");
  Serial.print(seconds);
  Serial.print("] ");
  
  // Print message
  Serial.println(message);
}

// LED Pattern:	Meaning
// 2 blue blinks:	Startup complete
// 1 green blink:	Sensor connected
// 2 red blinks:	Sensor disconnected
// Solid blue:	Reading temperature
// 1 quick green blink:	Successful reading
// 3 red blinks:	Read error
// Single blink every 10 sec:	Heartbeat (sensor connected)
// OFF:	No sensor / idle
