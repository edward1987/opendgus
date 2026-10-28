#pragma once
#include "Arduino.h"
#include "WiFi.h"
class PubSubClient {
 public:
  explicit PubSubClient(WiFiClient &) {}
  void setServer(const char *, int) {}
  bool setBufferSize(uint16_t) { return true; }
  void setCallback(void (*)(char *, byte *, unsigned int)) {}
  bool connected() { return false; }
  bool connect(const char *, const char *, const char *) { return true; }
  bool publish(const char *, const char *, bool = false) { return true; }
  bool subscribe(const char *) { return true; }
  bool loop() { return true; }
};
