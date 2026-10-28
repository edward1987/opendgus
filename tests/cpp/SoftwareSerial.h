#pragma once
#include "Arduino.h"
class SoftwareSerial : public HardwareSerial {
 public:
  SoftwareSerial(int, int) {}
};
