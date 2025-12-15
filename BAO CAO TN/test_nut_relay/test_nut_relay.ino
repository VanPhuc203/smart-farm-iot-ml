#define BUTTON_PIN 5   // Nút nhấn
#define RELAY_PIN 13   // Relay (LOW-active)

bool relayState = false;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 50;
bool lastButtonReading = HIGH;

void setup() {
    Serial.begin(115200);

    pinMode(BUTTON_PIN, INPUT_PULLUP); // Nút nhấn nối đất khi nhấn
    pinMode(RELAY_PIN, OUTPUT);
    
    digitalWrite(RELAY_PIN, HIGH); // Relay OFF (LOW-active)
}

void loop() {
    bool reading = digitalRead(BUTTON_PIN);

    // Xử lý chống rung nút nhấn
    if (reading != lastButtonReading) {
        lastDebounceTime = millis();
    }

    if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
        if (reading == LOW) { // Nút nhấn được nhấn
            relayState = !relayState; // Đảo trạng thái relay
            digitalWrite(RELAY_PIN, relayState ? LOW : HIGH); // LOW = ON
            Serial.printf("Button pressed. Relay is %s\n", relayState ? "ON" : "OFF");
            delay(200); // tránh nhấn liên tục
        }
    }

    lastButtonReading = reading;
}
