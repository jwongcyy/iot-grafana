// ESP32 Arduino Core 2.0+
// gateway_oled_display.ino
#include <esp_now.h>
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ========== OLED CONFIGURATION ==========
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C  // Try 0x3D if 0x3C doesn't work

// RuidaLongMaker GVDC Pins
#define SDA_PIN 8   // "D" pin on GVDC (GPIO8)
#define SCL_PIN 9   // "C" pin on GVDC (GPIO9)

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ========== ESP-NOW DATA STRUCTURE ==========
typedef struct sensor_data {
  uint8_t node_id;
  float temperature;
  uint32_t sequence;
  int8_t rssi;  // Will be filled by gateway
} sensor_data;

// ========== SENSOR TRACKING ==========
#define MAX_SENSORS 8
struct SensorInfo {
  float temperature;
  int8_t rssi;
  unsigned long lastSeen;  // Changed to unsigned long for millis()
  uint32_t packetCount;
  bool connected;
} sensors[MAX_SENSORS];

// ========== DISPLAY VARIABLES ==========
unsigned long lastDisplayUpdate = 0;
unsigned long lastStatsUpdate = 0;
uint8_t connectedSensors = 0;
int8_t avgRSSI = 0;
uint32_t totalPackets = 0;
String gatewayMAC;

// Display modes
enum DisplayMode { DASHBOARD, SENSOR_LIST, STATISTICS, SIGNAL_GRAPH };
DisplayMode currentMode = DASHBOARD;
unsigned long lastModeChange = 0;

// Signal history for graph
#define GRAPH_POINTS 32
int8_t signalHistory[GRAPH_POINTS] = {0};
int graphIndex = 0;

// ========== TIME UTILITY FUNCTIONS ==========
String getTimeAgo(unsigned long lastSeen) {
  unsigned long diff = millis() - lastSeen;
  
  if (diff < 1000) {
    return "Now";
  } else if (diff < 60000) {
    return String(diff / 1000) + "s";
  } else if (diff < 3600000) {
    return String(diff / 60000) + "m";
  } else {
    return String(diff / 3600000) + "h";
  }
}

String getFormattedTime(unsigned long lastSeen) {
  unsigned long diff = millis() - lastSeen;
  
  if (diff < 1000) return "Just now";
  if (diff < 60000) return String(diff / 1000) + " sec ago";
  if (diff < 3600000) return String(diff / 60000) + " min ago";
  if (diff < 86400000) return String(diff / 3600000) + " hour ago";
  return String(diff / 86400000) + " day ago";
}

// ========== DISPLAY FUNCTIONS ==========
void initOLED() {
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  
  delay(100);
  
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3D)) {
      Serial.println("OLED init failed!");
      while(1);
    }
  }
  
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.display();
  
  Serial.println("OLED initialized successfully");
}

void showSplashScreen() {
  display.clearDisplay();
  
  // Title
  display.setTextSize(2);
  display.setCursor(10, 5);
  display.print("ESP-NOW");
  display.setCursor(25, 25);
  display.print("Gateway");
  
  // MAC address
  display.setTextSize(1);
  display.setCursor(10, 50);
  display.print("MAC: ");
  display.print(gatewayMAC.substring(12));
  
  display.display();
  delay(2000);
}

void drawSignalBars(int x, int y, int8_t rssi) {
  // Convert RSSI to bars (1-4)
  int bars = 0;
  if (rssi >= -60) bars = 4;       // Excellent
  else if (rssi >= -70) bars = 3;  // Good
  else if (rssi >= -80) bars = 2;  // Fair
  else if (rssi >= -90) bars = 1;  // Poor
  
  // Draw 4 bars
  for (int i = 0; i < 4; i++) {
    int barHeight = (i + 1) * 3;
    int barY = y - barHeight;
    
    if (i < bars) {
      display.fillRect(x + i * 4, barY, 3, barHeight, SSD1306_WHITE);
    } else {
      display.drawRect(x + i * 4, barY, 3, barHeight, SSD1306_WHITE);
    }
  }
  
  // RSSI value
  display.setCursor(x + 18, y - 12);
  display.print(rssi);
  display.print("dB");
}

void updateSensorStats() {
  connectedSensors = 0;
  totalPackets = 0;
  int totalRSSI = 0;
  
  for (int i = 0; i < MAX_SENSORS; i++) {
    if (sensors[i].connected && (millis() - sensors[i].lastSeen < 300000)) {
      connectedSensors++;
      totalPackets += sensors[i].packetCount;
      totalRSSI += sensors[i].rssi;
    }
  }
  
  if (connectedSensors > 0) {
    avgRSSI = totalRSSI / connectedSensors;
  }
  
  // Update signal history for graph
  signalHistory[graphIndex] = avgRSSI;
  graphIndex = (graphIndex + 1) % GRAPH_POINTS;
}

// ========== DISPLAY MODES ==========
void showDashboard() {
  display.clearDisplay();
  
  // Header with timestamp
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("G");
  
  // Current time (uptime)
  unsigned long uptime = millis() / 1000;
  int hours = uptime / 3600;
  int minutes = (uptime % 3600) / 60;
  int seconds = uptime % 60;
  
  display.setCursor(15, 0);
  if (hours > 0) {
    display.print("UP:");
    display.print(hours);
    display.print("h");
    display.print(minutes);
    display.print("m");
  } else {
    display.print("UP:");
    display.print(minutes);
    display.print("m");
    display.print(seconds);
    display.print("s");
  }
  
  // Connected sensors count
  display.setCursor(80, 0);
  display.print("Sens:");
  display.print(connectedSensors);
  display.print("/");
  display.print(MAX_SENSORS);
  
  // Divider
  display.drawFastHLine(0, 9, 128, SSD1306_WHITE);
  
  if (connectedSensors > 0) {
    // Find strongest signal sensor
    int bestNode = -1;
    int8_t bestRSSI = -100;
    unsigned long mostRecent = 0;
    
    for (int i = 0; i < MAX_SENSORS; i++) {
      if (sensors[i].connected && sensors[i].lastSeen > mostRecent) {
        mostRecent = sensors[i].lastSeen;
        bestRSSI = sensors[i].rssi;
        bestNode = i;
      }
    }
    
    if (bestNode != -1) {
      // Large temperature display
      display.setTextSize(3);
      display.setCursor(10, 15);
      display.print(sensors[bestNode].temperature, 1);
      display.print("C");
      
      // Node info
      display.setTextSize(1);
      display.setCursor(10, 45);
      display.print("Node ");
      display.print(bestNode + 1);
      
      // Last seen timestamp
      display.setCursor(70, 45);
      display.print(getTimeAgo(sensors[bestNode].lastSeen));
      display.print(" ago");
      
      // Signal strength bars
      drawSignalBars(50, 52, bestRSSI);
    }
  } else {
    // No sensors connected
    display.setTextSize(2);
    display.setCursor(10, 20);
    display.print("No Sensor");
    
    display.setTextSize(1);
    display.setCursor(30, 43);
    display.print("Waiting...");
  }
  
  // Footer
  display.drawFastHLine(0, 52, 128, SSD1306_WHITE);
  
  // Current time
  display.setTextSize(1);
  display.setCursor(0, 55);
  display.print("Now:");
  
  unsigned long current = millis() / 1000;
  int m = (current % 3600) / 60;
  int s = current % 60;
  if (m < 10) display.print("0");
  display.print(m);
  display.print(":");
  if (s < 10) display.print("0");
  display.print(s);
  
  display.display();
}

void showSensorList() {
  display.clearDisplay();
  
  // Header with current time
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Sensors: ");
  display.print(connectedSensors);
  display.print("/");
  display.print(MAX_SENSORS);
  
  // Current time
  unsigned long current = millis() / 1000;
  int m = (current % 3600) / 60;
  int s = current % 60;
  display.setCursor(90, 0);
  display.print(m);
  display.print(":");
  if (s < 10) display.print("0");
  display.print(s);
  
  // Divider
  display.drawFastHLine(0, 9, 128, SSD1306_WHITE);
  
  // Sensor list (up to 5 sensors)
  int y = 12;
  int displayed = 0;
  
  for (int i = 0; i < MAX_SENSORS && displayed < 5; i++) {
    if (sensors[i].connected && (millis() - sensors[i].lastSeen < 300000)) {
      // Node ID
      display.setCursor(0, y);
      display.print("N");
      display.print(i + 1);
      
      // Temperature
      display.setCursor(15, y);
      display.print(sensors[i].temperature, 1);
      display.print("C");
      
      // Signal (compact)
      int8_t rssi = sensors[i].rssi;
      display.setCursor(45, y);
      display.print(rssi);
      display.print("dB");
      
      // Last seen time
      display.setCursor(70, y);
      String timeAgo = getTimeAgo(sensors[i].lastSeen);
      display.print(timeAgo);
      
      // Online indicator (dot)
      if (millis() - sensors[i].lastSeen < 30000) {  // 30 seconds = online
        display.fillCircle(125, y + 2, 2, SSD1306_WHITE);
      } else {
        display.drawCircle(125, y + 2, 2, SSD1306_WHITE);
      }
      
      y += 10;
      displayed++;
    }
  }
  
  if (displayed == 0) {
    display.setCursor(20, 30);
    display.print("No active sensors");
  }
  
  // Show inactive sensors count
  int inactive = 0;
  for (int i = 0; i < MAX_SENSORS; i++) {
    if (sensors[i].connected && (millis() - sensors[i].lastSeen >= 300000)) {
      inactive++;
    }
  }
  
  if (inactive > 0) {
    display.setCursor(0, 58);
    display.print(inactive);
    display.print(" inactive");
  }
  
  display.display();
}

void showSignalGraph() {
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Signal History");
  
  // Current time
  unsigned long current = millis() / 1000;
  int m = (current % 3600) / 60;
  int s = current % 60;
  display.setCursor(100, 0);
  display.print(m);
  display.print(":");
  if (s < 10) display.print("0");
  display.print(s);
  
  // Divider
  display.drawFastHLine(0, 9, 128, SSD1306_WHITE);
  
  // Graph area
  int graphX = 0;
  int graphY = 12;
  int graphWidth = 128;
  int graphHeight = 40;
  
  // Draw grid
  for (int i = 0; i <= 4; i++) {
    int y = graphY + i * (graphHeight / 4);
    display.drawFastHLine(graphX, y, graphWidth, SSD1306_WHITE);
  }
  
  // Draw graph
  int lastX = -1, lastY = -1;
  for (int i = 0; i < GRAPH_POINTS; i++) {
    int dataIndex = (graphIndex + i) % GRAPH_POINTS;
    if (signalHistory[dataIndex] != 0) {
      int x = graphX + (i * graphWidth / GRAPH_POINTS);
      // Map RSSI (-100 to -40) to graph height
      int y = graphY + graphHeight - 
              map(constrain(signalHistory[dataIndex], -100, -40), -100, -40, 0, graphHeight);
      
      if (lastX != -1) {
        display.drawLine(lastX, lastY, x, y, SSD1306_WHITE);
      }
      
      display.drawPixel(x, y, SSD1306_WHITE);
      lastX = x;
      lastY = y;
    }
  }
  
  // Quality labels
  display.setCursor(0, 55);
  display.print("Poor");
  display.setCursor(50, 55);
  display.print("Fair");
  display.setCursor(90, 55);
  display.print("Good");
  
  // Graph time range (32 * 2 seconds = 64 seconds)
  display.setCursor(110, 55);
  display.print("1m");
  
  display.display();
}

void showStatistics() {
  display.clearDisplay();
  
  // Header with timestamp
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Network Stats");
  
  // Current time
  unsigned long uptime = millis() / 1000;
  int hours = uptime / 3600;
  int minutes = (uptime % 3600) / 60;
  display.setCursor(90, 0);
  display.print("UP:");
  if (hours > 0) {
    display.print(hours);
    display.print("h");
  }
  display.print(minutes);
  display.print("m");
  
  // Divider
  display.drawFastHLine(0, 9, 128, SSD1306_WHITE);
  
  int y = 12;
  
  // Connected sensors
  display.setCursor(0, y);
  display.print("Active: ");
  display.print(connectedSensors);
  display.print("/");
  display.print(MAX_SENSORS);
  y += 10;
  
  // Average RSSI
  display.setCursor(0, y);
  display.print("Avg RSSI: ");
  display.print(avgRSSI);
  display.print(" dBm");
  y += 10;
  
  // Total packets
  display.setCursor(0, y);
  display.print("Total Pkts: ");
  display.print(totalPackets);
  y += 10;
  
  // Packet rate (per minute)
  display.setCursor(0, y);
  display.print("Rate: ");
  
  // Calculate packets per minute
  static unsigned long lastMinutePackets = 0;
  static unsigned long lastMinuteTime = 0;
  static float packetsPerMinute = 0;
  
  if (millis() - lastMinuteTime > 60000) {
    packetsPerMinute = (totalPackets - lastMinutePackets) * 60000.0 / (millis() - lastMinuteTime);
    lastMinutePackets = totalPackets;
    lastMinuteTime = millis();
  }
  
  display.print(packetsPerMinute, 1);
  display.print("/min");
  y += 10;
  
  // Oldest sensor time
  unsigned long oldest = 0;
  for (int i = 0; i < MAX_SENSORS; i++) {
    if (sensors[i].connected && sensors[i].lastSeen > oldest) {
      oldest = sensors[i].lastSeen;
    }
  }
  
  if (oldest > 0) {
    display.setCursor(0, y);
    display.print("Last Rx: ");
    display.print(getTimeAgo(oldest));
    display.print(" ago");
    y += 10;
  }
  
  // Memory usage
  display.setCursor(0, y);
  display.print("RAM: ");
  display.print(ESP.getFreeHeap() / 1024);
  display.print("KB free");
  
  display.display();
}

void updateDisplay() {
  updateSensorStats();
  
  switch(currentMode) {
    case DASHBOARD:
      showDashboard();
      break;
    case SENSOR_LIST:
      showSensorList();
      break;
    case SIGNAL_GRAPH:
      showSignalGraph();
      break;
    case STATISTICS:
      showStatistics();
      break;
  }
}

// ========== ESP-NOW CALLBACK ==========
void OnDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
  sensor_data data;
  
  if(len == sizeof(sensor_data)) {
    memcpy(&data, incomingData, sizeof(data));
    
    // Validate node ID
    if(data.node_id >= 1 && data.node_id <= MAX_SENSORS) {
      int idx = data.node_id - 1;
      
      // Update sensor data
      sensors[idx].temperature = data.temperature;
      sensors[idx].rssi = WiFi.RSSI(); // Current RSSI from this packet
      sensors[idx].lastSeen = millis();
      sensors[idx].packetCount++;
      sensors[idx].connected = true;
      
      // Print to serial with timestamp
      unsigned long uptime = millis() / 1000;
      int hours = uptime / 3600;
      int minutes = (uptime % 3600) / 60;
      int seconds = uptime % 60;
      
      Serial.printf("[%02d:%02d:%02d] ", hours, minutes, seconds);
      Serial.print("Node ");
      Serial.print(data.node_id);
      Serial.print(" | Temp: ");
      Serial.print(data.temperature, 1);
      Serial.print("°C | RSSI: ");
      Serial.print(sensors[idx].rssi);
      Serial.print("dB | Seq: ");
      Serial.println(data.sequence);
      
      // Update display
      updateDisplay();
    }
  }
}

// ========== SETUP ==========
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n═══════════════════════════════════════════");
  Serial.println("ESP-NOW GATEWAY WITH OLED DISPLAY");
  Serial.println("═══════════════════════════════════════════");
  
  // Initialize OLED
  initOLED();
  
  // Initialize WiFi
  WiFi.mode(WIFI_STA);
  gatewayMAC = WiFi.macAddress();
  
  Serial.print("Gateway MAC: ");
  Serial.println(gatewayMAC);
  
  // Show splash screen
  showSplashScreen();
  
  // Initialize ESP-NOW
  if(esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW initialization failed!");
    display.clearDisplay();
    display.setCursor(0, 0);
    display.print("ESP-NOW FAILED");
    display.display();
    delay(3000);
    ESP.restart();
  }
  
  esp_now_register_recv_cb(OnDataRecv);
  
  Serial.println("Gateway initialized successfully!");
  Serial.println("Waiting for sensor data...");
  
  // Initial display
  updateDisplay();
}

// ========== LOOP ==========
void loop() {
  // Update display every 2 seconds
  if(millis() - lastDisplayUpdate > 2000) {
    updateDisplay();
    lastDisplayUpdate = millis();
  }
  
  // Update statistics every 30 seconds
  if(millis() - lastStatsUpdate > 30000) {
    updateSensorStats();
    lastStatsUpdate = millis();
  }
  
  // Mark sensors as disconnected after 10 minutes
  for(int i = 0; i < MAX_SENSORS; i++) {
    if(sensors[i].connected && millis() - sensors[i].lastSeen > 600000) {
      sensors[i].connected = false;
    }
  }
  
  // Auto-cycle display modes every 15 seconds
  if(millis() - lastModeChange > 15000) {
    currentMode = (DisplayMode)((currentMode + 1) % 4);
    lastModeChange = millis();
    updateDisplay();
  }
  
  delay(100);
}
