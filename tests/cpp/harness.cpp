// Prints every frame the library sends ("TX ..") and every upload it reports ("UP vp value"), for a fixed
// script; tests/test_controller_libs.py runs the Python library through the same script and compares.
#include <stdio.h>
#include <vector>
#include "Arduino.h"
#include "OpenDGUS.h"

static unsigned long now_ms = 0;
HardwareSerial Serial, Serial1, Serial2;
unsigned long millis() { return now_ms; }
void yield() { now_ms += 1; }

struct Port : Stream {
  std::vector<uint8_t> rx, tx;
  size_t pos = 0;
  int available() override { return (int)(rx.size() - pos); }
  int read() override { return pos < rx.size() ? rx[pos++] : -1; }
  size_t write(uint8_t b) override { tx.push_back(b); return 1; }
  void feed(std::initializer_list<uint8_t> b) { rx.insert(rx.end(), b); }
  void flush(const char *tag) {
    printf("TX %s", tag);
    for (uint8_t b : tx) printf(" %02X", b);
    printf("\n");
    tx.clear();
  }
};

static void up(uint16_t vp, uint16_t v) { printf("UP %04X %04X\n", vp, v); }

int main() {
  Port p;
  DGUS d(p);
  d.onUpload(up);
  d.write(0x5000, 0x1234); p.flush("write");
  d.writeInt32(0x5002, -2); p.flush("int32");
  d.writeText(0x5010, "Hi", 8); p.flush("text");
  d.setPage(3); p.flush("page");
  d.setBrightness(10); p.flush("bright");
  p.feed({0x5A, 0xA5, 0x03, 0x82, 0x4F, 0x4B});                          // OK ack, ignored
  p.feed({0x5A, 0xA5, 0x06, 0x83, 0x50, 0x00, 0x01, 0x00, 0x2A});         // upload
  d.poll(); p.flush("poll");
  p.feed({0x00, 0x5A, 0xA5, 0x06, 0x83, 0x50, 0x04, 0x01, 0x00, 0x07,    // junk, upload, then the answer
          0x5A, 0xA5, 0x06, 0x83, 0x00, 0x14, 0x01, 0x00, 0x02});
  printf("PAGE %ld\n", (long)d.getPage()); p.flush("getpage");
  printf("TIMEOUT %ld\n", (long)d.read(0x5000)); p.flush("timeout");
  p.feed({0x5A, 0xA5, 0x08, 0x83, 0x00, 0x80, 0x02, 0x00, 0x14, 0x10, 0x38});
  d.setStandby(true, 10, 5, 100); p.flush("standby");
  DGUS c(p, true);
  c.onUpload(up);
  c.write(0x5000, 1); p.flush("crc");
  p.feed({0x5A, 0xA5, 0x08, 0x83, 0x50, 0x00, 0x01, 0x00, 0x05, 0x00, 0x00});  // bad CRC: dropped
  c.poll(); p.flush("crcbad");
  return 0;
}
