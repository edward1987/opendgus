// Minimal Arduino stand-in for host-side tests of the OpenDGUS library and generated sketches
// (tests/test_controller_libs.py, tests/test_codegen.py). Compile checks only: nothing here talks to hardware.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint8_t byte;
unsigned long millis();
void yield();
inline void delay(unsigned long) {}
#define OUTPUT 1
#define INPUT 0
#define HIGH 1
#define LOW 0
#define LED_BUILTIN 13
#define A0 14
#define SERIAL_8N1 0x06
inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline int digitalRead(int) { return 0; }
inline void analogWrite(int, int) {}
inline int analogRead(int) { return 512; }
inline long map(long x, long a, long b, long c, long d) { return (x - a) * (d - c) / (b - a) + c; }

class Stream {
 public:
  virtual ~Stream() {}
  virtual int available() = 0;
  virtual int read() = 0;
  virtual size_t write(uint8_t b) = 0;
  size_t write(const uint8_t *d, size_t n) { for (size_t i = 0; i < n; i++) write(d[i]); return n; }
};

class HardwareSerial : public Stream {
 public:
  void begin(unsigned long, int = SERIAL_8N1, int = -1, int = -1) {}
  void setTX(int) {}
  void setRX(int) {}
  int available() override { return 0; }
  int read() override { return -1; }
  size_t write(uint8_t) override { return 1; }
  using Stream::write;
};
extern HardwareSerial Serial, Serial1, Serial2;
