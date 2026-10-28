// OpenDGUS controller library for DWIN T5L (DGUS II) displays.
// Works on any Arduino core with a Stream: AVR (Nano, Uno, Mega), RP2040/RP2350 (Pico, Pico 2, Pico 2 W),
// ESP32, ESP8266, SAMD, STM32...
//
//   #include <OpenDGUS.h>
//   DGUS dgus(Serial1);
//   void onValue(uint16_t vp, uint16_t value) { ... }
//   void setup() { Serial1.begin(115200); dgus.onUpload(onValue); }
//   void loop()  { dgus.poll(); }
//
// Frames: 5A A5 <len> <cmd> <data> [CRC16-Modbus, low byte first]. 0x82 writes variables (VPs), 0x83 reads them
// and is also what the display sends when a control changes a variable.
// License: GPL-3.0 (OpenDGUS).
#pragma once
#include <Arduino.h>

class DGUS {
 public:
  typedef void (*UploadHandler)(uint16_t vp, uint16_t value);

  static const uint16_t VP_PAGE_NOW = 0x0014;
  static const uint16_t VP_TOUCH = 0x0016;     // 5A flag + state, X, Y; the controller clears the flag
  static const uint16_t VP_LED_NOW = 0x0031;
  static const uint16_t VP_CONFIG = 0x0080;    // D3 = 5A apply, D0 bit 2 = backlight standby
  static const uint16_t VP_LED = 0x0082;       // normal %, standby %, standby time (10 ms)
  static const uint16_t VP_PAGE_SET = 0x0084;  // 5A01 + page

  explicit DGUS(Stream &port, bool crc = false, uint16_t timeoutMs = 200);

  // variables
  void write(uint16_t vp, uint16_t value);
  void writeWords(uint16_t vp, const uint16_t *values, uint8_t count);
  void writeInt32(uint16_t vp, int32_t value);
  void writeText(uint16_t vp, const char *text, uint8_t length = 0);  // padded with 0xFF up to length
  bool read(uint16_t vp, uint16_t *out, uint8_t count = 1);         // false on timeout
  int32_t read(uint16_t vp);                                         // -1 on timeout
  void onUpload(UploadHandler handler) { handler_ = handler; }

  // pages and backlight
  void setPage(uint16_t page);
  int32_t getPage();
  void setBrightness(uint8_t percent);
  // Auto-dim by the display: `level` % after `seconds` without a touch (until power-off). Over 655 s the
  // library dims instead (soft dim).
  void setStandby(bool enabled, uint8_t level = 10, uint32_t seconds = 60, uint8_t normal = 100);

  // Screensaver: show `page` after `seconds` without a touch; the next touch goes back (to wakePage, or the
  // page that was showing if wakePage is -1). brightness -1 = unchanged. page -1 = off.
  void screensaver(int16_t page, uint32_t seconds, int16_t wakePage = -1, int8_t brightness = -1);
  bool screensaverActive() const { return saverActive_; }

  void touched();               // count as activity (the library also does this for every touch)
  uint32_t idleMs() const { return millis() - lastTouch_; }
  void poll();                  // call often from loop()

 private:
  Stream &port_;
  bool crc_;
  uint16_t timeout_;
  UploadHandler handler_ = nullptr;
  uint8_t buf_[64];
  uint8_t len_ = 0;
  uint32_t lastTouch_ = 0, pollAt_ = 0;
  uint8_t normal_ = 100;
  bool standby_ = false;
  uint8_t standbyLevel_ = 10;
  uint32_t standbySeconds_ = 60;
  bool softDim_ = false, softDimmed_ = false;
  int16_t saverPage_ = -1, saverWake_ = -1, saverFrom_ = -1;
  int8_t saverBrightness_ = -1;
  uint32_t saverMs_ = 0;
  bool saverActive_ = false;

  void send(uint8_t cmd, const uint8_t *data, uint8_t n);
  bool nextFrame(uint8_t *&body, uint8_t &n);
  void dispatch(const uint8_t *body, uint8_t n);
  void pump();
  void leaveSaver();
  void idleCheck();
  static uint16_t crc16(const uint8_t *d, uint8_t n, uint16_t crc = 0xFFFF);
};
