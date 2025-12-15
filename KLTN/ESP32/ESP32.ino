#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <SPI.h>

// --- KHAI BÁO PIN ---
// Cảm biến RS485 (NPK)
#define RO_PIN 32  
#define DI_PIN 33  
#define DE_PIN 25  
#define RE_PIN 26

// Thiết bị chấp hành
#define LIGHT_PIN 13
#define PUMP_PIN 14
#define FAN_PIN 27 

// Nút nhấn
#define LIGHT_BTN_PIN 5   
#define ROOF_BTN_PIN 4  
#define PUMP_BTN_PIN 17   
#define FAN_BTN_PIN 16

// Màn hình TFT ILI9341
#define TFT_CS   18
#define TFT_RST  19
#define TFT_DC   21
#define TFT_MOSI 22
#define TFT_SCLK 23

Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC, TFT_RST);

// --- CẤU HÌNH HỆ THỐNG ---
#define UPDATE_INTERVAL 5000
#define SERIAL_BAUD 115200
#define NPK_BAUD 4800 // Nếu nạp xong vẫn lỗi, hãy thử đổi thành 9600
#define BUFFER_SIZE 256

const char* SSID = "phuc";
const char* PASSWORD = "123456789";
const char* MQTT_SERVER = "4024dc14ff38445e99fe28aa9eb2eac3.s1.eu.hivemq.cloud";
const int MQTT_PORT = 8883;
const char* MQTT_USERNAME = "zed1127";
const char* MQTT_PASSWORD = "Phuc0912630035";

HardwareSerial npkSerial(1);  // UART1 cho RS485
WiFiClientSecure espClient;
PubSubClient client(espClient);

// --- CẤU HÌNH MODBUS (ĐÃ SỬA LẠI CRC CHUẨN) ---
// Đọc 7 thanh ghi: 01 03 00 00 00 07 -> CRC chuẩn là 08 B0
const byte QUERY_DATA[] = {0x01, 0x03, 0x00, 0x00, 0x00, 0x07, 0x08, 0xB0};
const size_t RESPONSE_SIZE = 19;

// --- ĐỘNG CƠ MÁI CHE ---
const int IN1 = 2;               
const int IN2 = 15;             
const int limitSwitchClose = 35; 
const int limitSwitchOpen = 34;

// --- BIẾN TRẠNG THÁI ---
bool lightStatus = false;
bool pumpStatus = false;
bool isOpening = false;  
bool isRunning = false; 
bool fanStatus = false; 

const unsigned long DEBOUNCE_DELAY = 50;    
const unsigned long DISPLAY_INTERVAL = 1000;
unsigned long lastDisplayUpdate = 0;

struct ButtonState {
    bool lastReading;
    bool state;
    bool lastState;
    unsigned long lastDebounceTime;
    bool changed;
};

ButtonState buttons[4] = {
    {HIGH, HIGH, HIGH, 0, false}, // Đèn
    {HIGH, HIGH, HIGH, 0, false}, // Mái che
    {HIGH, HIGH, HIGH, 0, false}, // Máy bơm
    {HIGH, HIGH, HIGH, 0, false}  // Quạt
};

struct LimitSwitchState {
    bool lastReading;
    bool state;
    unsigned long lastDebounceTime;
};
LimitSwitchState limitSwitches[2] = {
    {HIGH, HIGH, 0}, // Mở 
    {HIGH, HIGH, 0}  // Đóng
};

struct SoilData {
    float temperature;
    float humidity;
    uint16_t nitrogen;
    uint16_t phosphorus;
    uint16_t potassium;
    float ph;
};

struct DeviceStatus {
    bool light;
    bool roof;
    bool pump;
    bool fan;
};
DeviceStatus lastDeviceStatus = {false, false, false, false};
SoilData lastData = { -999, -999, 0, 0, 0, -999}; // Khởi tạo giá trị ảo để update lần đầu

// --- HÀM SETUP ---
void setup() {
    Serial.begin(SERIAL_BAUD);    

    // Khởi tạo màn hình
    SPI.begin(TFT_SCLK, -1, TFT_MOSI, TFT_CS);
    tft.begin();
    tft.setRotation(2);
    tft.fillScreen(ILI9341_BLACK);

    // Khởi tạo chân điều khiển RS485
    pinMode(DE_PIN, OUTPUT);
    pinMode(RE_PIN, OUTPUT);
    digitalWrite(DE_PIN, LOW);
    digitalWrite(RE_PIN, LOW);

    // Khởi tạo thiết bị
    pinMode(LIGHT_PIN, OUTPUT);
    pinMode(PUMP_PIN, OUTPUT);
    pinMode(FAN_PIN, OUTPUT);
    digitalWrite(LIGHT_PIN, LOW); // Relay kích LOW hoặc HIGH tùy module, ở đây để mặc định tắt
    digitalWrite(PUMP_PIN, LOW);
    digitalWrite(FAN_PIN, LOW);

    // Khởi tạo Motor
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(limitSwitchClose, INPUT); 
    pinMode(limitSwitchOpen, INPUT);  
    stopMotor(); 

    // Khởi tạo nút nhấn
    pinMode(LIGHT_BTN_PIN, INPUT_PULLUP);
    pinMode(ROOF_BTN_PIN, INPUT_PULLUP);
    pinMode(PUMP_BTN_PIN, INPUT_PULLUP);
    pinMode(FAN_BTN_PIN, INPUT_PULLUP);

    // Khởi tạo Serial RS485
    npkSerial.begin(NPK_BAUD, SERIAL_8N1, RO_PIN, DI_PIN);

    // Kết nối mạng
    setupWiFi();
    espClient.setInsecure(); // Bỏ qua xác thực chứng chỉ SSL (quan trọng cho ESP32 cũ)
    client.setServer(MQTT_SERVER, MQTT_PORT);
    client.setCallback(mqttCallback);

    // Giao diện khởi động
    tft.setTextSize(2);
    tft.setTextColor(ILI9341_WHITE);
    tft.setCursor(10, 10);
    tft.println("System Starting...");
    delay(1000);
    tft.fillScreen(ILI9341_BLACK);
    updateDeviceStatus(); // Vẽ trạng thái thiết bị lần đầu
}

void setupWiFi() {
    WiFi.begin(SSID, PASSWORD);
    Serial.printf("Connecting to %s", SSID);
    tft.setCursor(10, 30);
    tft.print("Wifi: Connecting...");
    
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 20) {
        delay(500);
        Serial.print(".");
        retries++;
    }
    if(WiFi.status() == WL_CONNECTED){
        Serial.printf("\nConnected, IP: %s\n", WiFi.localIP().toString().c_str());
        tft.fillRect(10, 30, 230, 20, ILI9341_BLACK);
        tft.setCursor(10, 30);
        tft.print("Wifi: OK");
    } else {
        Serial.println("\nWifi Connect Failed");
        tft.setCursor(10, 30);
        tft.print("Wifi: Failed");
    }
}

// --- XỬ LÝ MQTT ---
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String message = String((char*)payload, length);
    Serial.printf("MQTT [%s]: %s\n", topic, message.c_str());
    
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, payload, length);
    if (error) {
        Serial.printf("JSON Fail: %s\n", error.c_str());
        return;
    }

    // 1. Test kết nối
    if (strstr(topic, "iot/test") != NULL) {
        String clientId = doc["clientId"].as<String>();
        StaticJsonDocument<128> response;
        response["type"] = "connection_response";
        response["clientId"] = clientId;
        response["deviceId"] = "ESP32";
        response["status"] = "connected";        
        char buffer[128];
        serializeJson(response, buffer);
        client.publish("iot/test_response", buffer);
    }
    // 2. Yêu cầu trạng thái
    else if (strstr(topic, "iot/device/status_request/") != NULL) {
        String device = String(topic).substring(String(topic).lastIndexOf('/') + 1);
        StaticJsonDocument<64> response;
        bool status = false;
        
        if (device == "light") status = lightStatus;
        else if (device == "roof") status = isOpening;
        else if (device == "pump") status = pumpStatus;
        else if (device == "fan") status = fanStatus;
        
        response["status"] = status;
        char buffer[64];
        serializeJson(response, buffer);
        String respTopic = "iot/device/status_response/" + device;
        client.publish(respTopic.c_str(), buffer);
    }
    // 3. Điều khiển thiết bị
    else if (strstr(topic, "iot/device/control/") != NULL) {
        String device = String(topic).substring(String(topic).lastIndexOf('/') + 1);
        bool status = doc["status"].as<bool>();
        
        if (device == "light") {
            digitalWrite(LIGHT_PIN, status ? LOW : HIGH); // Logic ngược nếu dùng Relay kích thấp
            lightStatus = status;
        }
        else if (device == "roof") {
            if (status && !isRunning) {
                motorOpen(); isOpening = true; isRunning = true;
            } else if (!status && !isRunning) {
                motorClose(); isOpening = false; isRunning = true;
            }
        }
        else if (device == "pump") {
            digitalWrite(PUMP_PIN, status ? LOW : HIGH);
            pumpStatus = status;
        }
        else if (device == "fan") {
            digitalWrite(FAN_PIN, status ? LOW : HIGH);
            fanStatus = status;
        }    
        
        updateDeviceStatus();
        publishAllDeviceStatuses();
    }
}

void reconnectMQTT() {
    if (!client.connected()) {
        Serial.print("Connecting MQTT...");
        if (client.connect("ESP32Client_UniqueID", MQTT_USERNAME, MQTT_PASSWORD)) {
            Serial.println("OK");      
            client.subscribe("iot/device/control/#");
            client.subscribe("iot/device/status_request/#");
            client.subscribe("iot/test");            
            publishAllDeviceStatuses();
        } else {
            Serial.print("Fail rc=");
            Serial.print(client.state());
            Serial.println(" retry 5s");
        }
    }
}

// --- HÀM ĐỌC CẢM BIẾN (QUAN TRỌNG: ĐÃ SỬA) ---
bool readNPKData(SoilData& data) {
    // 1. Xóa sạch bộ đệm trước khi gửi để tránh đọc nhiễu cũ
    while (npkSerial.available()) {
        npkSerial.read();
    }

    // 2. Gửi lệnh Modbus
    digitalWrite(DE_PIN, HIGH);
    digitalWrite(RE_PIN, HIGH);
    delay(10); 
    npkSerial.write(QUERY_DATA, sizeof(QUERY_DATA));
    npkSerial.flush(); 
    digitalWrite(DE_PIN, LOW);
    digitalWrite(RE_PIN, LOW);

    // 3. Chờ phản hồi có Timeout
    unsigned long startTime = millis();
    while (npkSerial.available() < RESPONSE_SIZE) {
        if (millis() - startTime > 1000) { // Chờ tối đa 1 giây
            Serial.println("Error: Sensor Timeout");
            return false;
        }
        delay(10);
    }  

    // 4. Đọc dữ liệu
    byte response[RESPONSE_SIZE];
    npkSerial.readBytes(response, RESPONSE_SIZE);

    // DEBUG: In ra Hex để kiểm tra
    Serial.print("HEX: ");
    for(int i=0; i<RESPONSE_SIZE; i++) Serial.printf("%02X ", response[i]);
    Serial.println();

    // 5. Kiểm tra Header
    if (response[0] != 0x01 || response[1] != 0x03) {
        Serial.println("Error: Wrong Header");
        return false;
    }  

    // 6. Tính toán giá trị (Theo chuẩn 7 in 1)
    // Byte 3-4: Độ ẩm
    data.humidity = ((response[3] << 8) | response[4]) / 10.0;
    // Byte 5-6: Nhiệt độ
    data.temperature = ((response[5] << 8) | response[6]) / 10.0;
    // Byte 9-10: pH
    data.ph = ((response[9] << 8) | response[10]) / 10.0;
    // Byte 11-12: N
    data.nitrogen = (response[11] << 8) | response[12];
    // Byte 13-14: P
    data.phosphorus = (response[13] << 8) | response[14];
    // Byte 15-16: K
    data.potassium = (response[15] << 8) | response[16];
    
    return true;
}

// --- HIỂN THỊ & GỬI DỮ LIỆU ---
void publishData(const SoilData& data) {
    StaticJsonDocument<256> doc;  
    doc["temperature"] = data.temperature;
    doc["humidity"] = data.humidity;
    doc["nitrogen"] = data.nitrogen;
    doc["phosphorus"] = data.phosphorus;
    doc["potassium"] = data.potassium;
    doc["ph"] = data.ph;

    char jsonBuffer[BUFFER_SIZE];
    size_t n = serializeJson(doc, jsonBuffer);
    client.publish("iot/sensor/data", jsonBuffer);
    Serial.println(jsonBuffer);

    // Cập nhật màn hình TFT (Chỉ vẽ lại khi có thay đổi để đỡ nháy)
    // Tách riêng từng mục để code gọn hơn
    if (abs(data.temperature - lastData.temperature) >= 0.1) {
        tft.fillRect(10, 10, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 10);
        tft.setTextColor(ILI9341_YELLOW);
        tft.printf("T: %.1f C", data.temperature);
        lastData.temperature = data.temperature;
    }
    if (abs(data.humidity - lastData.humidity) >= 0.1) {
        tft.fillRect(10, 40, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 40);
        tft.setTextColor(ILI9341_CYAN);
        tft.printf("H: %.1f %%", data.humidity);
        lastData.humidity = data.humidity;
    }
    if (data.nitrogen != lastData.nitrogen) {
        tft.fillRect(10, 70, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 70);
        tft.setTextColor(ILI9341_WHITE);
        tft.printf("N: %u mg/kg", data.nitrogen);
        lastData.nitrogen = data.nitrogen;
    }
    if (data.phosphorus != lastData.phosphorus) {
        tft.fillRect(10, 100, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 100);
        tft.setTextColor(ILI9341_WHITE);
        tft.printf("P: %u mg/kg", data.phosphorus);
        lastData.phosphorus = data.phosphorus;
    }
    if (data.potassium != lastData.potassium) {
        tft.fillRect(10, 130, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 130);
        tft.setTextColor(ILI9341_WHITE);
        tft.printf("K: %u mg/kg", data.potassium);
        lastData.potassium = data.potassium;
    }
    if (abs(data.ph - lastData.ph) >= 0.1) {
        tft.fillRect(10, 160, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 160);
        tft.setTextColor(ILI9341_MAGENTA);
        tft.printf("PH: %.1f", data.ph);
        lastData.ph = data.ph;
    }
}

// --- ĐIỀU KHIỂN MOTOR ---
void motorOpen() {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
}
void motorClose() {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
}
void stopMotor() {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
}

// --- CÔNG TẮC HÀNH TRÌNH ---
bool readLimitSwitch(uint8_t pin, LimitSwitchState &ls) {
    bool reading = digitalRead(pin);
    if (reading != ls.lastReading) {
        ls.lastDebounceTime = millis();
    }
    if ((millis() - ls.lastDebounceTime) > DEBOUNCE_DELAY) {
        ls.state = reading;
    }
    ls.lastReading = reading;
    return ls.state;
}

// --- XỬ LÝ NÚT NHẤN ---
void handleButton(int index, uint8_t btnPin, uint8_t devicePin, bool &deviceStatus, const char* mqttTopic) {
    bool reading = digitalRead(btnPin);
    ButtonState &btn = buttons[index];    
    
    if (reading != btn.lastReading) {
        btn.lastDebounceTime = millis();
        btn.changed = false;
    }    
    
    if ((millis() - btn.lastDebounceTime) > DEBOUNCE_DELAY) {       
        if (reading != btn.state) {
            btn.state = reading;            
            // Xử lý khi nhấn xuống (LOW)
            if (btn.state == LOW && !btn.changed) {
                if (index == 1) { // Mái che
                    if (!isRunning) {
                        if (isOpening) {
                            motorClose(); isOpening = false; isRunning = true;
                        } else {
                            motorOpen(); isOpening = true; isRunning = true;
                        }
                    }
                } else { // Thiết bị khác
                    deviceStatus = !deviceStatus;
                    digitalWrite(devicePin, deviceStatus ? LOW : HIGH); // Trigger LOW
                }
                
                // Gửi MQTT cập nhật
                if (client.connected()) {
                    StaticJsonDocument<64> doc;
                    doc["status"] = (index == 1) ? isOpening : deviceStatus;
                    char buffer[64];
                    serializeJson(doc, buffer);
                    client.publish(mqttTopic, buffer);
                }
                updateDeviceStatus();
                btn.changed = true;
            }
        }
    }    
    btn.lastReading = reading;
}

// --- CẬP NHẬT TRẠNG THÁI MÀN HÌNH ---
void updateDeviceStatus() {
    // Chỉ vẽ lại nếu trạng thái thay đổi để màn hình không bị giật
    if (lightStatus != lastDeviceStatus.light) {
        tft.fillRect(10, 190, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 190);
        tft.setTextColor(lightStatus ? ILI9341_GREEN : ILI9341_RED);
        tft.printf("LIGHT: %s", lightStatus ? "ON " : "OFF");
        lastDeviceStatus.light = lightStatus;
    }
    if (isOpening != lastDeviceStatus.roof) {
        tft.fillRect(10, 220, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 220);
        tft.setTextColor(isOpening ? ILI9341_GREEN : ILI9341_RED);
        tft.printf("ROOF : %s", isOpening ? "OPEN " : "CLOSE");
        lastDeviceStatus.roof = isOpening;
    }
    if (pumpStatus != lastDeviceStatus.pump) {
        tft.fillRect(10, 250, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 250);
        tft.setTextColor(pumpStatus ? ILI9341_GREEN : ILI9341_RED);
        tft.printf("PUMP : %s", pumpStatus ? "ON " : "OFF");
        lastDeviceStatus.pump = pumpStatus;
    }
    if (fanStatus != lastDeviceStatus.fan) {
        tft.fillRect(10, 280, 230, 30, ILI9341_BLACK);
        tft.setCursor(10, 280);
        tft.setTextColor(fanStatus ? ILI9341_GREEN : ILI9341_RED);
        tft.printf("FAN  : %s", fanStatus ? "ON " : "OFF");
        lastDeviceStatus.fan = fanStatus;
    }
}

void publishAllDeviceStatuses() {
    StaticJsonDocument<64> doc;
    char buffer[64];
    
    doc["status"] = lightStatus; serializeJson(doc, buffer);
    client.publish("iot/device/status/light", buffer);
    
    doc["status"] = isOpening; serializeJson(doc, buffer);
    client.publish("iot/device/status/roof", buffer);
    
    doc["status"] = pumpStatus; serializeJson(doc, buffer);
    client.publish("iot/device/status/pump", buffer);
    
    doc["status"] = fanStatus; serializeJson(doc, buffer);
    client.publish("iot/device/status/fan", buffer);
}

// --- MAIN LOOP ---
void loop() {
    static unsigned long lastUpdate = 0;
    
    if (!client.connected()) {
        reconnectMQTT();
    }
    client.loop();

    // Xử lý nút nhấn
    handleButton(0, LIGHT_BTN_PIN, LIGHT_PIN, lightStatus, "iot/device/status/light");
    handleButton(1, ROOF_BTN_PIN, 0, isOpening, "iot/device/status/roof");
    handleButton(2, PUMP_BTN_PIN, PUMP_PIN, pumpStatus, "iot/device/status/pump");
    handleButton(3, FAN_BTN_PIN, FAN_PIN, fanStatus, "iot/device/status/fan");

    // Xử lý mái che tự động dừng
    if (isRunning) {
        bool openState = readLimitSwitch(limitSwitchOpen, limitSwitches[0]);
        bool closeState = readLimitSwitch(limitSwitchClose, limitSwitches[1]);
        
        // Gặp hành trình mở -> Dừng
        if (!openState && isOpening) {
            stopMotor(); isRunning = false;
            updateDeviceStatus();
            if (client.connected()) {
                client.publish("iot/device/status/roof", "{\"status\":true}");
            }
        } 
        // Gặp hành trình đóng -> Dừng
        else if (!closeState && !isOpening) {
            stopMotor(); isRunning = false;
            updateDeviceStatus();
            if (client.connected()) {
                client.publish("iot/device/status/roof", "{\"status\":false}");
            }
        }
    }

    // Đọc cảm biến định kỳ
    if (millis() - lastUpdate >= UPDATE_INTERVAL) {
        SoilData data;
        if (readNPKData(data)) {
            publishData(data);
        } else {
            // Hiển thị lỗi nhưng không xóa màn hình để tránh nháy đen thui
            Serial.println("Read NPK Failed"); 
        }
        lastUpdate = millis();
    }
}