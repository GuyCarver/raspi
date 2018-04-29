# PCA9865 16 servo controller driver for Raspberry PI

from smbus import SMBus
from time import sleep

class pca9865(object):
  '''16 servo contoller. Use index 0-15 for the servo #.'''

  _ADDRESS = 0x40
  _MODE1 = 0
  _PRESCALE = 0xFE

  _LED0_ON_L = 0x6                              #We only use LED0 and offset 0-16 from it.
#  _LED0_ON_H = const(0x7)
#  _LED0_OFF_L = const(0x8)
#  _LED0_OFF_H = const(0x9)

#  _ALLLED_ON_L = const(0xFA)
#  _ALLLED_ON_H = const(0xFB)
#  _ALLLED_OFF_L = const(0xFC)
#  _ALLLED_OFF_H = const(0xFD)

  _DEFAULTFREQ = 60
  _MINPULSE = 120
  _MAXPULSE = 600

  def __init__( self, aFreq = 60, aLoc = 1 ):
    '''aLoc = 1 by default and should only be 0 if on older model cards.'''
    self.i2c = SMBus(aLoc)
    self._buffer = [0] * 4 #Can't use a bytearray with the write function.
    sleep(.050)
    self.reset()
    self._minmax(self._MINPULSE, self._MAXPULSE)
    self.setfreq(aFreq)

  def _minmax( self, aMin, aMax ):
    '''Set min/max and calculate range.'''
    self._min = aMin
    self._max = aMax
    self._range = aMax - aMin

  def _read( self, aLoc ) :
    '''Read 8 bit value and return.'''
    return self.i2c.read_byte_data(self._ADDRESS, aLoc)

  def _write( self, aValue, aLoc ):
    """Write 8 bit integer aVal to given address aLoc."""
    self.i2c.write_byte_data(self._ADDRESS, aLoc, aValue)

  def _writebuffer( self, aBuffer, aLoc ):
    """Write buffer to given address."""
    self.i2c.write_i2c_block_data(self._ADDRESS, aLoc, aBuffer)

  def reset( self ):
    '''Reset the controller and set default frequency.'''
    self._write(0, self._MODE1)
    self.setfreq(self._DEFAULTFREQ)

  def setfreq( self, aFreq ):
    '''Set frequency for all servos.  A good value is 60hz (default).'''
    aFreq *= 0.9  #Correct for overshoot in frequency setting.
    prescalefloat = (6103.51562 / aFreq) - 1  #25000000 / 4096 / freq.
    prescale = int(prescalefloat + 0.5)

    oldmode = self._read(self._MODE1)
    newmode = (oldmode & 0x7F) | 0x10
    self._write(newmode, self._MODE1)
    self._write(prescale, self._PRESCALE)
    self._write(oldmode, self._MODE1)
    sleep(0.050)
    self._write(oldmode | 0xA1, self._MODE1)  #This sets the MODE1 register to turn on auto increment.

  def _setpwm( self, aServo, aOn, aOff ):
    '''aServo = 0-15.
       aOn = 16 bit on value.
       aOff = 16 bit off value.
    '''
    if 0 <= aServo <= 15:
      #Data = on-low, on-high, off-low and off-high.  That's 4 bytes each servo.
      loc = self._LED0_ON_L + (aServo * 4)
#    print(loc)
      self._buffer[0] = aOn & 0xFF
      self._buffer[1] = aOn >> 8
      self._buffer[2] = aOff & 0xFF
      self._buffer[3] = aOff >> 8
      self._writebuffer(self._buffer, loc)
    else:
      raise Exception('Servo index {} out of range.'.format(str(aServo)))

  def off( self, aServo ):
    '''Turn off a servo.'''
    self._setpwm(aServo, 0, 0)

  def alloff( self ):
    '''Turn all servos off.'''
    for x in range(0, 16):
      self.off(x)

  def set( self, aServo, aPerc ):
    '''Set the 0-100%. If < 0 turns servo off.'''
    if aPerc < 0 :
      self.off(aServo)
    else:
      val = self._min + ((self._range * aPerc) // 100)
      self._setpwm(aServo, 0, val)

  def setangle( self, aServo, aAngle ):
    '''Set angle -90 to +90.  < -90 is off.'''
    #((a + 90.0) * 100.0) / 180.0
    perc = int((aAngle + 90.0) * 0.5556)  #Convert angle +/- 90 to 0-100%
    self.set(aServo, perc)
