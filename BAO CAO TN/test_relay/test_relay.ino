#define BUTTON_PIN 17
#define RELAY_PIN 14

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);
  Serial.println("\n=== Test đọc nút ===");
}

void loop() {
  bool state = digitalRead(BUTTON_PIN);
  Serial.print("Button state = ");
  Serial.println(state ? "HIGH" : "LOW");
  delay(1000);
}
