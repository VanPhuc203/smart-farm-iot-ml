#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>

// ==== Cấu hình chân LCD ====
#define TFT_CS    18
#define TFT_RST   19
#define TFT_DC    21
#define TFT_MOSI  22
#define TFT_SCK  23

// ==== Cấu hình nút nhấn ====
#define BTN1 4
#define BTN2 16
#define BTN3 17
#define BTN4 5

// ==== Khởi tạo SPI & LCD ====
SPIClass spi = SPIClass(VSPI);
Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC, TFT_RST);

void setup() {
  Serial.begin(115200);
  delay(200);

  // Bắt đầu SPI với chân tùy chỉnh
  spi.begin(TFT_SCK, -1, TFT_MOSI);
  SPI.begin(TFT_SCK, -1, TFT_MOSI);

  // Khởi động LCD
  tft.begin();
  tft.setRotation(1);
  tft.fillScreen(ILI9341_BLACK);
  tft.setTextSize(2);
  tft.setTextColor(ILI9341_YELLOW);
  tft.setCursor(30, 20);
  tft.println("ESP32 + 4 BUTTONS");
  tft.setCursor(30, 40);
  tft.println("ILI9341 TEST");

  // Cấu hình nút nhấn (kích hoạt pull-up nội)
  pinMode(BTN1, INPUT_PULLUP);
  pinMode(BTN2, INPUT_PULLUP);
  pinMode(BTN3, INPUT_PULLUP);
  pinMode(BTN4, INPUT_PULLUP);
}

void loop() {
  // Đọc trạng thái nút
  int b1 = digitalRead(BTN1);
  int b2 = digitalRead(BTN2);
  int b3 = digitalRead(BTN3);
  int b4 = digitalRead(BTN4);

  // In ra Serial để kiểm tra
  Serial.printf("BTN1:%d BTN2:%d BTN3:%d BTN4:%d\n", b1, b2, b3, b4);

  // Xóa vùng hiển thị cũ
  tft.fillRect(20, 70, 280, 120, ILI9341_BLACK);

  // Hiển thị trạng thái từng nút
  tft.setTextSize(2);

  tft.setCursor(40, 80);
  tft.setTextColor(b1 == LOW ? ILI9341_GREEN : ILI9341_RED);
  tft.println(b1 == LOW ? "BTN1: PRESSED" : "BTN1: RELEASED");

  tft.setCursor(40, 100);
  tft.setTextColor(b2 == LOW ? ILI9341_GREEN : ILI9341_RED);
  tft.println(b2 == LOW ? "BTN2: PRESSED" : "BTN2: RELEASED");

  tft.setCursor(40, 120);
  tft.setTextColor(b3 == LOW ? ILI9341_GREEN : ILI9341_RED);
  tft.println(b3 == LOW ? "BTN3: PRESSED" : "BTN3: RELEASED");

  tft.setCursor(40, 140);
  tft.setTextColor(b4 == LOW ? ILI9341_GREEN : ILI9341_RED);
  tft.println(b4 == LOW ? "BTN4: PRESSED" : "BTN4: RELEASED");

  delay(200);
}
