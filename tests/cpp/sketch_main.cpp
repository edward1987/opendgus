// Links a generated sketch (compiled as C++) into a host program and runs setup() and a few loop()s.
#include "Arduino.h"
#include "WiFi.h"
HardwareSerial Serial, Serial1, Serial2;
WiFiClass WiFi;
static unsigned long now_ms = 0;
unsigned long millis() { return now_ms; }
void yield() { now_ms += 1; }
void setup();
void loop();
int main() {
  setup();
  for (int i = 0; i < 100; i++) { now_ms += 50; loop(); }
  return 0;
}
