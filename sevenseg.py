
from time import time, sleep, localtime

from wiringpi import wiringPiSetupGpio, pinMode, digitalRead, digitalWrite, GPIO
wiringPiSetupGpio()

class sevenseg(object):
  _CMD1 = 0x40
  _CMD2 = 0xC0
  _CMD3 = 0x80

  #      A
  #     ---
  #  F |   | B
  #     -G-
  #  E |   | C
  #     ---
  #      D
  # XGFEDCBA
  _numbertable = [
    0b00111111, #0
    0b00000110, #1
    0b01011011, #2
    0b01001111, #3
    0b01100110, #4
    0b01101101, #5
    0b01111101, #6
    0b00000111, #7
    0b01111111, #8
    0b01101111, #9
    0b01110111, #A
    0b01111100, #B
    0b00111001, #C
    0b01011110, #D
    0b01111001, #E
    0b01110001, #F
    0b00000000, #space
    0b01000000  #dash
  ]

  @staticmethod
  def flipdigit( aByte ) :
    bit = 1
    f = 0
    #swap bits 0-2 with 3-5 (0-3, 1-4, 2-5)
    for x in range(3):
      f |= (aByte & bit) << 3
      bit <<= 1
    for x in range(3, 6):
      f |= (aByte & bit) >> 3
      bit <<= 1
    f |= aByte & 0xC0 #Keep the rest of the bits.
    return f

  """docstring for 7seg"""
  def __init__(self, clk, dio ):
    self._clk = clk
    self._dio = dio
    self._brightness = 7
    self._colon = False
    self._flip = False
    self._buffer = bytearray(4)

    pinMode(self._clk, GPIO.INPUT)
    pinMode(self._dio, GPIO.INPUT)
    digitalWrite(self._clk, GPIO.LOW)
    digitalWrite(self._dio, GPIO.LOW)

  @property
  def colon( self ) : return self._colon

  @colon.setter
  def colon( self, aValue ) :
    self._colon = aValue

  @property
  def flip( self ) : return self._flip

  @flip.setter
  def flip( self, aValue ) :
    self._flip = aValue

  @property
  def brightness( self ) : return self._brightness

  @brightness.setter
  def brightness( self, aValue ) :
    self._brightness = aValue & 0xF
    self._write_comm1()
    self._write_comm3()

  def _start(self):
    pinMode(self._dio, GPIO.OUTPUT)
    sleep(0.001)

  def _stop(self):
    pinMode(self._dio, GPIO.OUTPUT)
    sleep(0.001)
    pinMode(self._clk, GPIO.INPUT)
    sleep(0.001)
    pinMode(self._dio, GPIO.INPUT)
    sleep(0.001)

  def _write_comm1(self):
    self._start()
    self._write_byte(self._CMD1)
    self._stop()

  def _write_comm3(self):
    self._start()
    self._write_byte(self._CMD3 + self._brightness + 7)
    self._stop()

  def _write_byte(self, b):
    # send each bit
    for i in range(8):
      pinMode(self._clk, GPIO.OUTPUT)
      sleep(0.001)
      pinMode(self._dio, GPIO.INPUT if b & 1 else GPIO.OUTPUT)
      sleep(0.001)
      pinMode(self._clk, GPIO.INPUT)
      sleep(0.001)
      b >>= 1
    pinMode(self._clk, GPIO.OUTPUT)
    sleep(0.001)
    pinMode(self._clk, GPIO.INPUT)
    sleep(0.001)
    pinMode(self._clk, GPIO.OUTPUT)
    sleep(0.001)

  def clear( self ) :
    for v in self._buffer:
      v = 0

  def display( self ) :
    colonloc = -2 if self.flip else 1
    if self.colon :
      self._buffer[colonloc] |= 0x80
    else:
      self._buffer[colonloc] &= ~0x80

    self._write_comm1()
    self._start()
    self._write_byte(self._CMD2)

    #If screen flipped we need to flip the digits and write in reverse oder.
    if self.flip:
      sloc = len(self._buffer) - 1
      for x in range(sloc, -1, -1):
        b = self.flipdigit(self._buffer[x])
        self._write_byte(b)
    else:
      for b in self._buffer:
        self._write_byte(b)

    self._stop()
    self._write_comm3()

  def data( self, aIndex, aValue ) :
    self._buffer[aIndex] = aValue

  def digit( self, aIndex, aValue ) :
    if 0 <= aValue < len(self._numbertable) :
      self.data(aIndex, self._numbertable[aValue])

  def char(self, aIndex, char):
    """Display a character 0-9, a-f, space or dash."""
    o = ord(char)
    c = -1
    # space
    if o == 32:
      c = 16
    # dash
    if o == 45:
      c = 17
    # uppercase A-F
    if 65 <= o <= 70:
      c = o - 55
    # lowercase a-f
    if 97 <= o <= 102:
      c = o - 87
    # 0-9
    if 48 <= o <= 57:
      c = o - 48

    self.digit(aIndex, c)

def clock(tm) :
  while True:
    t = localtime()
    tm.colon = t.tm_sec & 1
    tm.digit(0, t.tm_hour // 10)
    tm.digit(1, t.tm_hour % 10)
    tm.digit(2, t.tm_min // 10)
    tm.digit(3, t.tm_min % 10)
    tm.display()

    sleep(1 - time() % 1)

