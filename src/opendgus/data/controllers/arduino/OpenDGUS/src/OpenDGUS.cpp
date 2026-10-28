// OpenDGUS controller library - see OpenDGUS.h. License: GPL-3.0.
#include "OpenDGUS.h"

DGUS::DGUS(Stream &port, bool crc, uint16_t timeoutMs) : port_(port), crc_(crc), timeout_(timeoutMs) {
  lastTouch_ = millis();
}

uint16_t DGUS::crc16(const uint8_t *d, uint8_t n, uint16_t crc) {
  for (uint8_t i = 0; i < n; i++) {
    crc ^= d[i];
    for (uint8_t k = 0; k < 8; k++) crc = (crc & 1) ? (crc >> 1) ^ 0xA001 : crc >> 1;
  }
  return crc;
}

void DGUS::send(uint8_t cmd, const uint8_t *data, uint8_t n) {
  uint8_t head[4] = {0x5A, 0xA5, (uint8_t)(n + 1 + (crc_ ? 2 : 0)), cmd};
  port_.write(head, 4);
  port_.write(data, n);
  if (crc_) {
    uint16_t c = crc16(data, n, crc16(&cmd, 1));
    uint8_t t[2] = {(uint8_t)(c & 0xFF), (uint8_t)(c >> 8)};
    port_.write(t, 2);
  }
}

// Byte-wise parser: 5A A5 len body[len]. Returns true with body/n set when a whole (CRC-checked) frame is in.
bool DGUS::nextFrame(uint8_t *&body, uint8_t &n) {
  while (port_.available()) {
    uint8_t c = port_.read();
    if (len_ == 0) {
      if (c == 0x5A) buf_[len_++] = c;
    } else if (len_ == 1) {
      if (c == 0xA5) buf_[len_++] = c;
      else len_ = (c == 0x5A) ? 1 : 0;
    } else if (len_ == 2) {
      if (c == 0 || c > sizeof(buf_) - 3) { len_ = 0; continue; }   // too long for us: resync
      buf_[len_++] = c;
    } else {
      buf_[len_++] = c;
      if (len_ == 3 + buf_[2]) {
        uint8_t m = buf_[2];
        len_ = 0;
        if (crc_) {
          if (m < 3) continue;
          uint16_t want = buf_[3 + m - 2] | (buf_[3 + m - 1] << 8);
          if (crc16(buf_ + 3, m - 2) != want) continue;     // damaged frame
          m -= 2;
        }
        body = buf_ + 3;
        n = m;
        return true;
      }
    }
  }
  return false;
}

void DGUS::dispatch(const uint8_t *body, uint8_t n) {
  if (n < 6 || body[0] != 0x83) return;                     // 0x82 "OK" acknowledgements are ignored
  uint16_t vp = (body[1] << 8) | body[2];
  if (vp < 0x1000) return;                                  // late answer to a system-variable read
  uint16_t value = (body[4] << 8) | body[5];
  touched();
  if (handler_) handler_(vp, value);
}

void DGUS::pump() {
  uint8_t *body;
  uint8_t n;
  while (nextFrame(body, n)) dispatch(body, n);
}

void DGUS::writeWords(uint16_t vp, const uint16_t *values, uint8_t count) {
  uint8_t d[2 + 2 * 16];
  if (count > 16) count = 16;
  d[0] = vp >> 8;
  d[1] = vp & 0xFF;
  for (uint8_t i = 0; i < count; i++) {
    d[2 + 2 * i] = values[i] >> 8;
    d[3 + 2 * i] = values[i] & 0xFF;
  }
  send(0x82, d, 2 + 2 * count);
}

void DGUS::write(uint16_t vp, uint16_t value) { writeWords(vp, &value, 1); }

void DGUS::writeInt32(uint16_t vp, int32_t value) {
  uint16_t w[2] = {(uint16_t)((uint32_t)value >> 16), (uint16_t)(value & 0xFFFF)};
  writeWords(vp, w, 2);
}

void DGUS::writeText(uint16_t vp, const char *text, uint8_t length) {
  uint8_t d[2 + 64];
  uint8_t n = 0;
  d[0] = vp >> 8;
  d[1] = vp & 0xFF;
  uint8_t max = length ? length : 62;
  if (max > 62) max = 62;
  while (text[n] && n < max) { d[2 + n] = text[n]; n++; }
  if (n < max) { d[2 + n++] = 0xFF; if (n < max) d[2 + n++] = 0xFF; }   // DGUS end-of-text marker
  if (n & 1) d[2 + n++] = 0xFF;
  send(0x82, d, 2 + n);
}

bool DGUS::read(uint16_t vp, uint16_t *out, uint8_t count) {
  uint8_t q[3] = {(uint8_t)(vp >> 8), (uint8_t)(vp & 0xFF), count};
  send(0x83, q, 3);
  uint32_t t0 = millis();
  while (millis() - t0 < timeout_) {
    uint8_t *body;
    uint8_t n;
    while (nextFrame(body, n)) {
      if (n >= 4 + 2 * count && body[0] == 0x83 && ((body[1] << 8) | body[2]) == vp && body[3] == count) {
        for (uint8_t i = 0; i < count; i++) out[i] = (body[4 + 2 * i] << 8) | body[5 + 2 * i];
        return true;
      }
      dispatch(body, n);
    }
    yield();
  }
  return false;
}

int32_t DGUS::read(uint16_t vp) {
  uint16_t v;
  return read(vp, &v, 1) ? (int32_t)v : -1;
}

void DGUS::setPage(uint16_t page) {
  uint16_t w[2] = {0x5A01, page};
  writeWords(VP_PAGE_SET, w, 2);
}

int32_t DGUS::getPage() { return read(VP_PAGE_NOW); }

void DGUS::setBrightness(uint8_t percent) {
  uint8_t d[3] = {VP_LED >> 8, VP_LED & 0xFF, (uint8_t)(percent > 100 ? 100 : percent)};
  send(0x82, d, 3);   // the one-byte form always applies (hardware-checked)
}

void DGUS::setStandby(bool enabled, uint8_t level, uint32_t seconds, uint8_t normal) {
  normal_ = normal;
  standbyLevel_ = level;
  standbySeconds_ = seconds;
  softDim_ = enabled && seconds > 655;
  standby_ = enabled && !softDim_;
  uint32_t ticks = seconds * 100UL;
  uint16_t w[2] = {(uint16_t)((normal << 8) | level), (uint16_t)(standby_ ? (ticks > 0xFFFF ? 0xFFFF : (ticks ? ticks : 1)) : 0)};
  writeWords(VP_LED, w, 2);
  uint16_t cfg[2];
  if (read(VP_CONFIG, cfg, 2)) {
    uint16_t c[2] = {(uint16_t)(0x5A00 | (cfg[0] & 0xFF)), (uint16_t)(standby_ ? (cfg[1] | 4) : (cfg[1] & ~4))};
    writeWords(VP_CONFIG, c, 2);
  }
  if (!standby_) setBrightness(normal);
}

void DGUS::screensaver(int16_t page, uint32_t seconds, int16_t wakePage, int8_t brightness) {
  saverPage_ = page;
  saverMs_ = seconds * 1000UL;
  saverWake_ = wakePage;
  saverBrightness_ = brightness;
}

void DGUS::touched() {
  lastTouch_ = millis();
  if (saverActive_) leaveSaver();
  if (softDimmed_) {
    softDimmed_ = false;
    setBrightness(normal_);
  }
}

void DGUS::leaveSaver() {
  saverActive_ = false;
  int16_t back = saverWake_ >= 0 ? saverWake_ : saverFrom_;
  if (back >= 0) setPage(back);
  if (saverBrightness_ >= 0) {
    if (standby_) setStandby(true, standbyLevel_, standbySeconds_, normal_);
    else setBrightness(normal_);
  }
}

void DGUS::idleCheck() {
  if (saverPage_ < 0 && !softDim_) return;
  if (millis() - pollAt_ < 200) return;
  pollAt_ = millis();
  uint16_t t;
  if (read(VP_TOUCH, &t, 1) && (t >> 8) == 0x5A) {          // touches anywhere, also where no control is
    write(VP_TOUCH, 0);
    touched();
    return;
  }
  uint32_t idle = idleMs();
  if (softDim_ && !softDimmed_ && idle >= standbySeconds_ * 1000UL) {
    softDimmed_ = true;
    setBrightness(standbyLevel_);
  }
  if (saverPage_ >= 0 && !saverActive_ && idle >= saverMs_) {
    int32_t page = getPage();
    if (page >= 0 && page != saverPage_) {
      saverFrom_ = page;
      setPage(saverPage_);
      if (saverBrightness_ >= 0) setBrightness(saverBrightness_);
      saverActive_ = true;
    }
  }
}

void DGUS::poll() {
  pump();
  idleCheck();
}
