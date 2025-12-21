
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
} sensor_data;

// ========== SENSOR TRACKING ==========
#define MAX_SENSORS 8
struct SensorInfo {
  float temperature;
  int8_t rssi;
  uint32_t lastSeen;
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

// ========== ESP-NOW CALLBACK (FIXED FOR ESP32 CORE 2.0+) ==========
// This works with ESP32 Arduino Core 2.0 and later
void OnDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
  sensor_data data;
  
  if(len == sizeof(sensor_data)) {
    memcpy(&data, incomingData, sizeof(data));
    
    // Validate node ID
    if(data.node_id >= 1 && data.node_id <= MAX_SENSORS) {
      int idx = data.node_id - 1;
      
      // Update sensor data
      sensors[idx].temperature = data.temperature;
      sensors[idx].rssi = recv_info->rx_ctrl->rssi; // RSSI from received packet
      sensors[idx].lastSeen = millis();
      sensors[idx].packetCount++;
      sensors[idx].connected = true;
      
      // Print to serial for debugging
      Serial.print("Node ");
      Serial.print(data.node_id);
      Serial.print(" | Temp: ");
      Serial.print(data.temperature, 1);
      Serial.print("°C | RSSI: ");
      Serial.print(sensors[idx].rssi);
      Serial.print("dB | Seq: ");
      Serial.println(data.sequence);
      
      // Auto-switch to dashboard when new data arrives
      if(currentMode != DASHBOARD && millis() - lastModeChange > 10000) {
        currentMode = DASHBOARD;
      }
      
      // Update display
      updateDisplay();
    }
  }
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

void drawBattery(int x, int y, int percent) {
  // Battery outline
  display.drawRect(x, y, 20, 10, SSD1306_WHITE);
  display.fillRect(x + 20, y + 2, 3, 6, SSD1306_WHITE);
  
  // Fill based on percentage
  int fillWidth = map(percent, 0, 100, 0, 18);
  if (fillWidth > 0) {
    display.fillRect(x + 1, y + 1, fillWidth, 8, SSD1306_WHITE);
  }
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
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("GATEWAY");
  
  // Connected sensors count
  display.setCursor(65, 0);
  display.print("Active:");
  display.print(connectedSensors);
  display.print("/");
  display.print(MAX_SENSORS);
  
  // Divider
  display.drawFastHLine(0, 9, 128, SSD1306_WHITE);
  
  if (connectedSensors > 0) {
    // Find strongest signal sensor
    int bestNode = -1;
    int8_t bestRSSI = -100;
    
    for (int i = 0; i < MAX_SENSORS; i++) {
      if (sensors[i].connected && sensors[i].rssi > bestRSSI) {
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
      display.setCursor(10, 55);
      display.print("Node ");
      display.print(bestNode + 1);
      
      // Signal strength bars
      drawSignalBars(50, 62, bestRSSI);
    }
  } else {
    // No sensors connected
    display.setTextSize(2);
    display.setCursor(15, 20);
    display.print("No Sensor");
    
    display.setTextSize(1);
    display.setCursor(30, 53);
    display.print("Waiting...");
  }
  
  // // Footer
  // display.drawFastHLine(0, 52, 128, SSD1306_WHITE);
  
  // // Average signal
  // display.setTextSize(1);
  // display.setCursor(0, 58);
  // display.print("Avg:");
  // display.print(avgRSSI);
  // display.print("dB");
  
  // // Uptime
  // display.setCursor(70, 58);
  // display.print("UP:");
  // display.print(millis() / 60000);
  // display.print("m");
  
  display.display();
}

void showSensorList() {
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Connected: ");
  display.print(connectedSensors);
  
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
      display.setCursor(18, y);
      display.print(sensors[i].temperature, 1);
      display.print("C");
      
      // Signal bars (mini)
      int8_t rssi = sensors[i].rssi;
      int bars = 0;
      if (rssi >= -60) bars = 3;
      else if (rssi >= -70) bars = 2;
      else if (rssi >= -80) bars = 1;
      
      for (int b = 0; b < 3; b++) {
        if (b < bars) {
          display.fillRect(60 + b * 4, y + 3 - (b + 1), 3, (b + 1) * 2, SSD1306_WHITE);
        }
      }
      
      // RSSI value
      display.setCursor(80, y);
      display.print(rssi);
      display.print("dB");
      
      // Packet count
      display.setCursor(110, y);
      display.print(sensors[i].packetCount);
      
      y += 10;
      displayed++;
    }
  }
  
  if (displayed == 0) {
    display.setCursor(20, 30);
    display.print("No active sensors");
  }
  
  display.display();
}

void showSignalGraph() {
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Signal Now:");
  display.print(avgRSSI);
  display.print("dB");
  
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
  
  display.display();
}

void showStatistics() {
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Network Statistics");
  
  // Divider
  display.drawFastHLine(0, 9, 128, SSD1306_WHITE);
  
  int y = 12;
  
  // Connected sensors
  display.setCursor(0, y);
  display.print("Sensors: ");
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
  
  // // Gateway MAC (short)
  // display.setCursor(0, y);
  // display.print("MAC: ");
  // display.print(gatewayMAC.substring(12));
  // y += 10;
  
  // Uptime
  display.setCursor(0, y);
  display.print("Uptime: ");
  display.print(millis() / 60000);
  display.print("m");
  y += 10;
  
  // Free memory
  display.setCursor(0, y);
  display.print("RAM: ");
  display.print(ESP.getFreeHeap() / 1024);
  display.print("KB");
  
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
  Serial.print("WiFi Channel: ");
  Serial.println(WiFi.channel());
  
  // Show splash screen
  showSplashScreen();
  
  // Initialize ESP-NOW
  Serial.print("Initializing ESP-NOW... ");
  if(esp_now_init() != ESP_OK) {
    Serial.println("FAILED!");
    display.clearDisplay();
    display.setCursor(0, 0);
    display.print("ESP-NOW FAILED");
    display.display();
    delay(3000);
    ESP.restart();
  }
  Serial.println("SUCCESS");
  
  // Register receive callback (FIXED SIGNATURE)
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
  
  // Auto-cycle display modes every 10 seconds
  if(millis() - lastModeChange > 10000) {
    currentMode = (DisplayMode)((currentMode + 1) % 4);
    lastModeChange = millis();
    updateDisplay();
  }
  
  delay(100);
}
