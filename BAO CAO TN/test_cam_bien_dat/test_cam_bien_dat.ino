#include <HardwareSerial.h>

#define RXD2 32   // RO_PIN (RS485 -> ESP32 RX)
#define TXD2   33   // DI_PIN (RS485 -> ESP32 TX)35
#define DE_PIN 25 // Driver Enable
#define RE_PIN 26 // Receiver Enable

#define SERIAL_BAUD 115200
#define NPK_BAUD 4800
#define UPDATE_INTERVAL 5000
#define RESPONSE_SIZE 19

const byte QUERY_DATA[] = {0x01, 0x03, 0x00, 0x00, 0x00, 0x07, 0x04, 0x08};

struct SoilData {
  float temperature;
  float humidity;
  uint16_t nitrogen;
  uint16_t phosphorus;
  uint16_t potassium;
  float ph;
};

HardwareSerial npkSerial(1); // UART1

void setup() {
  Serial.begin(SERIAL_BAUD);
  npkSerial.begin(NPK_BAUD, SERIAL_8N1, RXD2, TXD2);

  pinMode(DE_PIN, OUTPUT);
  pinMode(RE_PIN, OUTPUT);
  digitalWrite(DE_PIN, LOW);
  digitalWrite(RE_PIN, LOW);

  Serial.println("Khởi tạo cảm biến NPK...");
}

bool readNPKData(SoilData &data) {
  digitalWrite(DE_PIN, HIGH);
  digitalWrite(RE_PIN, HIGH);
  delay(10);

  npkSerial.write(QUERY_DATA, sizeof(QUERY_DATA));
  npkSerial.flush();

  digitalWrite(DE_PIN, LOW);
  digitalWrite(RE_PIN, LOW);
  delay(200);

  if (npkSerial.available() < RESPONSE_SIZE) {
    Serial.println("❌ Không nhận đủ dữ liệu từ cảm biến!");
    return false;
  }

  byte response[RESPONSE_SIZE];
  npkSerial.readBytes(response, RESPONSE_SIZE);

  if (response[0] != 0x01) {
    Serial.println("⚠️ Dữ liệu phản hồi không hợp lệ");
    return false;
  }

  data.humidity = ((response[3] << 8) | response[4]) / 10.0;
  data.temperature = ((response[5] << 8) | response[6]) / 10.0;
  data.ph = ((response[9] << 8) | response[10]) / 10.0;
  data.nitrogen = (response[11] << 8) | response[12];
  data.phosphorus = (response[13] << 8) | response[14];
  data.potassium = (response[15] << 8) | response[16];

  return true;
}

void printData(const SoilData &data) {
  Serial.printf("🌱 T: %.2f°C | H: %.2f%% | N: %u | P: %u | K: %u | pH: %.2f\n",
                data.temperature, data.humidity, data.nitrogen,
                data.phosphorus, data.potassium, data.ph);
}

void loop() {
  static unsigned long lastUpdate = 0;
  if (millis() - lastUpdate >= UPDATE_INTERVAL) {
    SoilData data;
    if (readNPKData(data)) {
      printData(data);
    } else {
      Serial.println("⚠️ Không đọc được dữ liệu cảm biến!");
    }
    lastUpdate = millis();
  }
}
