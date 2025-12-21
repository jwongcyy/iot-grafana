// Shows connected sensors, signal strength, battery, and network status

#include <esp_now.h>
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ========== OLED CONFIG ==========
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

// RuidaLongMaker GVDC Pins
#define SDA_PIN 8   // "D" pin on GVDC (GPIO8)
#define SCL_PIN 9   // "C" pin on GVDC (GPIO9)

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ========== ESP-NOW CONFIG ==========
typedef struct struct_message {
  uint8_t node_id;
  float temperature;
  uint8_t battery;
  uint32_t sequence;
} struct_message;

#define MAX_SENSORS 8  // Maximum number of sensors to track
struct SensorData {
  float temperature;
  uint8_t battery;
  int8_t rssi;         // Signal strength (-dBm)
  unsigned long lastSeen;
  uint32_t packetCount;
  bool connected;
} sensors[MAX_SENSORS];

// ========== DISPLAY VARIABLES ==========
unsigned long lastDisplayUpdate = 0;
unsigned long lastStatsUpdate = 0;
uint8_t connectedCount = 0;
uint8_t totalPackets = 0;
int8_t avgRSSI = 0;
String gatewayMAC;

// WiFi status (for future expansion)
bool wifiEnabled = false;  // Set to true if using WiFi + MQTT

// ========== OLED DISPLAY MODES ==========
enum DisplayMode {
  MODE_DASHBOARD,      // Main dashboard
  MODE_SENSOR_LIST,    // Detailed sensor list
  MODE_SIGNAL_GRAPH,   // Signal strength graph
  MODE_STATS           // Statistics view
};

DisplayMode currentMode = MODE_DASHBOARD;
unsigned long lastModeChange = 0;

// ========== DISPLAY FUNCTIONS ==========

void initOLED() {
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  
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
  
  // Logo/Title
  display.setTextSize(2);
  display.setCursor(15, 5);
  display.print("ESP-NOW");
  display.setCursor(25, 25);
  display.print("Gateway");
  
  // Version info
  display.setTextSize(1);
  display.setCursor(35, 50);
  display.print("v1.0");
  
  display.display();
  delay(2000);
}

void drawSignalBars(int x, int y, int8_t rssi) {
  // Convert RSSI to bars (1-4)
  int bars = 0;
  if (rssi > -60) bars = 4;       // Excellent
  else if (rssi > -70) bars = 3;  // Good
  else if (rssi > -80) bars = 2;  // Fair
  else if (rssi > -90) bars = 1;  // Poor
  
  // Draw 4 bars
  for (int i = 0; i < 4; i++) {
    int barHeight = (i + 1) * 3;
    if (i < bars) {
      display.fillRect(x + i * 4, y - barHeight, 3, barHeight, SSD1306_WHITE);
    } else {
      display.drawRect(x + i * 4, y - barHeight, 3, barHeight, SSD1306_WHITE);
    }
  }
  
  // RSSI value
  display.setCursor(x + 18, y - 10);
  display.print(rssi);
  display.print("dB");
}

void drawBattery(int x, int y, uint8_t percent) {
  // Battery outline
  display.drawRect(x, y, 20, 10, SSD1306_WHITE);
  display.fillRect(x + 20, y + 2, 3, 6, SSD1306_WHITE);
  
  // Fill based on percentage
  int fillWidth = map(percent, 0, 100, 0, 18);
  if (fillWidth > 0) {
    display.fillRect(x + 1, y + 1, fillWidth, 8, SSD1306_WHITE);
  }
  
  // Percentage text
  if (percent < 100) display.setCursor(x + 25, y);
  else display.setCursor(x + 22, y);
  display.print(percent);
  display.print("%");
}

void updateSensorStats() {
  connectedCount = 0;
  totalPackets = 0;
  int totalRSSI = 0;
  
  for (int i = 0; i < MAX_SENSORS; i++) {
    if (sensors[i].connected && (millis() - sensors[i].lastSeen < 300000)) { // 5 minutes
      connectedCount++;
      totalPackets += sensors[i].packetCount;
      totalRSSI += sensors[i].rssi;
    }
  }
  
  if (connectedCount > 0) {
    avgRSSI = totalRSSI / connectedCount;
  }
}

// ========== DISPLAY MODES ==========

void showDashboard() {
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("ESP-NOW Gateway");
  
  // Connected sensors count
  display.setCursor(90, 0);
  display.print("Sensors:");
  display.print(connectedCount);
  
  // Divider
  display.drawFastHLine(0, 9, 128, SSD1306_WHITE);
  
  // Large center display
  if (connectedCount > 0) {
    // Show strongest signal sensor
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
      display.setCursor(10, 45);
      display.print("Node ");
      display.print(bestNode + 1);
      
      // Signal strength bars
      drawSignalBars(50, 52, bestRSSI);
      
      // Battery indicator
      drawBattery(90, 40, sensors[bestNode].battery);
    }
  } else {
    // No sensors connected
    display.setTextSize(2);
    display.setCursor(10, 20);
    display.print("No Sensor");
  }
  
  // Footer
  display.drawFastHLine(0, 54, 128, SSD1306_WHITE);
  
  // Average signal strength
  display.setTextSize(1);
  display.setCursor(0, 58);
  display.print("Avg:");
  display.print(avgRSSI);
  display.print("dB");
  
  // Uptime
  display.setCursor(60, 58);
  display.print("UP:");
  display.print(millis() / 60000);
  display.print("m");
  
  display.display();
}

void showSensorList() {
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Connected Sensors:");
  display.print(connectedCount);
  
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
      display.setCursor(20, y);
      display.print(sensors[i].temperature, 1);
      display.print("C");
      
      // Battery icon
      int battX = 60;
      display.drawRect(battX, y - 1, 12, 6, SSD1306_WHITE);
      display.fillRect(battX + 12, y + 1, 2, 2, SSD1306_WHITE);
      
      int fillWidth = map(sensors[i].battery, 0, 100, 0, 10);
      if (fillWidth > 0) {
        display.fillRect(battX + 1, y, fillWidth, 4, SSD1306_WHITE);
      }
      
      // Signal bars (simplified)
      int8_t rssi = sensors[i].rssi;
      int bars = 0;
      if (rssi > -60) bars = 3;
      else if (rssi > -70) bars = 2;
      else if (rssi > -80) bars = 1;
      
      for (int b = 0; b < 3; b++) {
        if (b < bars) {
          display.fillRect(80 + b * 4, y + 3 - (b + 1), 3, (b + 1) * 2, SSD1306_WHITE);
        } else {
          display.drawRect(80 + b * 4, y + 3 - (b + 1), 3, (b + 1) * 2, SSD1306_WHITE);
        }
      }
      
      // RSSI value
      display.setCursor(100, y);
      display.print(rssi);
      display.print("dB");
      
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
  static int graphData[32] = {0};
  static int graphIndex = 0;
  
  // Store average RSSI in graph buffer
  graphData[graphIndex] = avgRSSI;
  graphIndex = (graphIndex + 1) % 32;
  
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Signal Strength History");
  
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
  for (int i = 0; i < 32; i++) {
    int dataIndex = (graphIndex + i) % 32;
    if (graphData[dataIndex] != 0) {
      int x = graphX + (i * graphWidth / 32);
      // Map RSSI (-100 to -40) to graph height
      int y = graphY + graphHeight - 
              map(constrain(graphData[dataIndex], -100, -40), -100, -40, 0, graphHeight);
      
      if (lastX != -1) {
        display.drawLine(lastX, lastY, x, y, SSD1306_WHITE);
      }
      
      display.drawPixel(x, y, SSD1306_WHITE);
      lastX = x;
      lastY = y;
    }
  }
  
  // Legend
  display.setCursor(0, 55);
  display.print("Weak");
  display.setCursor(50, 55);
  display.print("Good");
  display.setCursor(100, 55);
  display.print("Excel");
  
  // Current value
  display.setCursor(0, 45);
  display.print("Now:");
  display.print(avgRSSI);
  display.print("dB");
  
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
  display.print("Connected: ");
  display.print(connectedCount);
  display.print("/");
  display.print(MAX_SENSORS);
  y += 10;
  
  // Average RSSI
  display.setCursor(0, y);
  display.print("Avg Signal: ");
  display.print(avgRSSI);
  display.print(" dBm");
  y += 10;
  
  // Total packets
  display.setCursor(0, y);
  display.print("Total Pkts: ");
  display.print(totalPackets);
  y += 10;
  
  // Gateway MAC
  display.setCursor(0, y);
  display.print("MAC: ");
  display.print(gatewayMAC.substring(12));
  y += 10;
  
  // Uptime
  display.setCursor(0, y);
  display.print("Uptime: ");
  display.print(millis() / 1000);
  display.print("s");
  y += 10;
  
  // Free heap
  display.setCursor(0, y);
  display.print("Free RAM: ");
  display.print(ESP.getFreeHeap() / 1024);
  display.print("KB");
  
  display.display();
}

void updateDisplay() {
  updateSensorStats();  // Update statistics first
  
  switch(currentMode) {
    case MODE_DASHBOARD:
      showDashboard();
      break;
    case MODE_SENSOR_LIST:
      showSensorList();
      break;
    case MODE_SIGNAL_GRAPH:
      showSignalGraph();
      break;
    case MODE_STATS:
      showStatistics();
      break;
  }
}

void changeDisplayMode() {
  currentMode = (DisplayMode)((currentMode + 1) % 4);
  lastModeChange = millis();
  
  // Show mode name briefly
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(10, 20);
  
  switch(currentMode) {
    case MODE_DASHBOARD: display.print("Dashboard Mode"); break;
    case MODE_SENSOR_LIST: display.print("Sensor List Mode"); break;
    case MODE_SIGNAL_GRAPH: display.print("Signal Graph Mode"); break;
    case MODE_STATS: display.print("Statistics Mode"); break;
  }
  
  display.display();
  delay(800);
}

// ========== ESP-NOW CALLBACK ==========
void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  struct_message msg;
  if(len == sizeof(struct_message)) {
    memcpy(&msg, data, sizeof(msg));
    
    // Validate node ID
    if(msg.node_id >= 1 && msg.node_id <= MAX_SENSORS) {
      int idx = msg.node_id - 1;
      
      // Update sensor data
      sensors[idx].temperature = msg.temperature;
      sensors[idx].battery = msg.battery;
      sensors[idx].rssi = info->rx_ctrl->rssi;
      sensors[idx].lastSeen = millis();
      sensors[idx].packetCount++;
      sensors[idx].connected = true;
      
      // Print to serial
      Serial.print("Node ");
      Serial.print(msg.node_id);
      Serial.print(" | Temp: ");
      Serial.print(msg.temperature, 1);
      Serial.print("C | Batt: ");
      Serial.print(msg.battery);
      Serial.print("% | RSSI: ");
      Serial.print(info->rx_ctrl->rssi);
      Serial.print("dB | Seq: ");
      Serial.println(msg.sequence);
      
      // Auto-return to dashboard on new data
      if(currentMode != MODE_DASHBOARD && millis() - lastModeChange > 10000) {
        currentMode = MODE_DASHBOARD;
      }
      
      // Update display
      updateDisplay();
    }
  }
}

// ========== SETUP ==========
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("====================================");
  Serial.println("ESP-NOW GATEWAY WITH ADVANCED OLED");
  Serial.println("Shows connected sensors & signal strength");
  Serial.println("====================================");
  
  // Initialize OLED
  initOLED();
  showSplashScreen();
  
  // Initialize WiFi for ESP-NOW
  WiFi.mode(WIFI_STA);
  gatewayMAC = WiFi.macAddress();
  
  Serial.print("Gateway MAC: ");
  Serial.println(gatewayMAC);
  
  // Display MAC on OLED
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Gateway MAC:");
  display.setCursor(0, 10);
  display.print(gatewayMAC);
  display.setCursor(0, 25);
  display.print("Mode: ESP-NOW");
  display.setCursor(0, 40);
  display.print("Waiting for sensors..");
  display.display();
  delay(2000);
  
  // Initialize ESP-NOW
  if(esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    display.clearDisplay();
    display.setCursor(0, 0);
    display.print("ESP-NOW FAILED");
    display.display();
    while(1);
  }
  
  esp_now_register_recv_cb(OnDataRecv);
  
  Serial.println("ESP-NOW initialized. Waiting for sensors..");
  
  // Initial display
  updateDisplay();
}

// ========== LOOP ==========
void loop() {
  // Update display every 2 seconds
  static unsigned long lastUpdate = 0;
  if(millis() - lastUpdate > 2000) {
    updateDisplay();
    lastUpdate = millis();
  }
  
  // Mark sensors as disconnected after 10 minutes
  for(int i = 0; i < MAX_SENSORS; i++) {
    if(sensors[i].connected && millis() - sensors[i].lastSeen > 600000) {
      sensors[i].connected = false;
    }
  }
  
  // Optional: Add button to change display mode
  // if(digitalRead(BUTTON_PIN) == LOW) {
  //   delay(50); // Debounce
  //   if(digitalRead(BUTTON_PIN) == LOW) {
  //     changeDisplayMode();
  //     while(digitalRead(BUTTON_PIN) == LOW); // Wait for release
  //   }
  // }
  
  delay(100);
}
