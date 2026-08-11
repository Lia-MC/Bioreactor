/*
1. Start SoftWire and set its buffers.
2. Select bank 1.
3. Read register 0x5A; it must equal 0x81 (AS7343 chip ID).
4. Select bank 0.
5. Set ENABLE bit 0 (PON) to power the sensor.
6. Set gain, ATIME, and ASTEP.
7. Select the channel/auto-SMUX mode. 

sending sensor2.startMeasurement(), dataReady(), readChannel() into I2C messages

*/

#include <SoftWire.h>

//Softwire other than TwoWire

class AS7343Soft {

private:
  SoftWire &wire;

  static const uint8_t AS7343_ADDRESS = 0x39;

  // Write one byte into one AS7343 register
  bool write8(uint8_t reg, uint8_t value) {
    wire.beginTransmission(AS7343_ADDRESS);
    wire.write(reg);     // Which register?
    wire.write(value);   // What value goes into it?

    // 0 means the sensor acknowledged the message
    return wire.endTransmission(true) == 0;
  }

  // Read one byte from one AS7343 register
  bool read8(uint8_t reg, uint8_t &value) {
    wire.beginTransmission(AS7343_ADDRESS);
    wire.write(reg);  // Tell the sensor which register we want

    // false = keep the connection open for the read
    if (wire.endTransmission(false) != 0) {
      return false;
    }

    // Ask for one byte, then end the connection
    if (wire.requestFrom(AS7343_ADDRESS, (uint8_t)1, (uint8_t)true) != 1) {
      return false;
    }

    value = wire.read();  // Put the received byte into value
    return true;
  }

  // Read a two-byte light reading
  bool read16(uint8_t reg, uint16_t &value) {
    wire.beginTransmission(AS7343_ADDRESS);
    wire.write(reg);

    if (wire.endTransmission(false) != 0) {
      return false;
    }

    if (wire.requestFrom(AS7343_ADDRESS, (uint8_t)2, (uint8_t)true) != 2) {
      return false;
    }

    uint8_t lowByte = wire.read();
    uint8_t highByte = wire.read();

    // Join two 8-bit bytes into one 16-bit number
    value = (uint16_t)lowByte | ((uint16_t)highByte << 8);
    return true;
  }

  // Change one on/off bit while preserving the other bits
  bool setBit(uint8_t reg, uint8_t bit, bool enabled) {
    uint8_t value;

    if (!read8(reg, value)) {
      return false;
    }

    if (enabled) {
      value |= (1 << bit);   // Turn this bit on
    } else {
      value &= ~(1 << bit);  // Turn this bit off
    }

    return write8(reg, value);
  }

  // Select AS7343 register bank 0 or bank 1
  bool setBank(bool bank1) {
    return setBit(0xBF, 4, bank1);
  }

public:
  //varaible bus of type SoftWire initilized as wire
  AS7343Soft(SoftWire &bus) : wire(bus) {}


  bool begin() {
    //verify chip ID, if its not AS7343 then you shouldn't do AS7343 functions
    uint8_t chipID;

    //switch to bank1 for chip-ID register, read the value, and check if it matches AS7343 address
    if(!setBank(true) || !read8(0x5A, chipID) || chipID != 0x81) return false;

    //AS7343_ID = 0x5A (register)
    //AS7343_CHIP_ID = 0x81
    //I2C address = 0x39

    //switch to measurement mode
    if (!setBank(false)) return false;

    // Turn sensor power on: ENABLE register, bit 0
    if (!setBit(0x80, 0, true)) return false;

    // Set 64x gain
    if (!write8(0xC6, 0x07)) return false;

    // Set integration time
    if (!write8(0x81, 29)) return false;       // ATIME
    if (!write8(0xD4, 599 & 0xFF)) return false; // ASTEP low byte
    if (!write8(0xD5, 599 >> 8)) return false;   // ASTEP high byte

    // Use 18-channel Auto-SMUX mode
    uint8_t cfg20;
    if (!read8(0xD6, cfg20)) return false;
    cfg20 = (cfg20 & ~0x60) | 0x60;
    if (!write8(0xD6, cfg20)) return false;

    return true; //means everything worked

  }

  //clear any old measurement
  void stopMeasurement() {
    setBit(0x80, 1, false);
  }

  bool startMeasurement() {
    stopMeasurement();
    return setBit(0x80, 1, true);  //SP_EN
  }


  bool dataReady() {
    uint8_t status2;
    return read8(0x90, status2) && (status2 & 0x40);
  }

  bool readLightFXL(uint16_t &fxlValue) {
  uint8_t astatus;

  // Latch the completed measurement into the data registers
  if (!read8(0x94, astatus)) {
    return false;
  }
  //reading ASTATUS makes finished measurement available for reading

  // Fxl register 0x95
  return read16(0x95, fxlValue);
  //CHANGE VALUE HERE HERE HERE HERE HERE HERE HERE
}
  }; 
