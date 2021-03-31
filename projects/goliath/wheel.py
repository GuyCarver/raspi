#!/usr/bin/env python3

import RPi.GPIO as GPIO

#--------------------------------------------------------
class wheel(object):
  '''The wheels are run by an n298 dual h-bridge. The forward, backward and speed
      pins for the n298 are attached to the pca9865. Forward and backward pins are
      always set to either 1.0 or 0.0.  The speed is the only variable value.
      This was preferred to running separate wires to the raspi. A 3 wire servo cable
      was used for all 3 pins connecting to 3 consecutive signal pins on the pca.'''

  _scale = 1.0
  _MINSPEED = .2
#   _MAXSPEED = 1.0
  _SPEEDRANGE = 1.0 - _MINSPEED

#--------------------------------------------------------
  def __init__( self, pca, si, fi, bi ):
    ''' Initialize the wheel with pca, speed, forward and back indexes.
        Also the pin number for the speedomoter. '''
    super(wheel, self).__init__()

    self._pca = pca
    self._si = si
    self._fi = fi
    self._bi = bi
    GPIO.setup(fi, GPIO.OUT)
    GPIO.setup(bi, GPIO.OUT)

    self._name = ''
   
#--------------------------------------------------------
  @property
  def name( self ):
    return self._name

#--------------------------------------------------------
  @name.setter
  def name( self, aValue ):
    self._name = aValue

#--------------------------------------------------------
  @property
  def dist( self ): return self._so._dist

#--------------------------------------------------------
  @property
  def time( self ): return self._so._time

#--------------------------------------------------------
  @classmethod
  def clamp( cls, aValue ) :
    ''' Convert float aValue to value between min and max speed. '''
    return (min(1.0, aValue) * wheel._SPEEDRANGE) + wheel._MINSPEED

#--------------------------------------------------------
  @classmethod
  def changegear( cls, aValue ):
    ''' Set the speed scale to simulate gears. '''
    cls._scale += aValue
    cls._scale = max(0.2, min(cls._scale, 1.0))

#--------------------------------------------------------
  def _write( self, aValues ):
    ''' Write data to the pca. '''
    fwd, back, spd = aValues

    #Set full range of PWM signal to get a value from 0 to 1 on the pin.
    GPIO.output(self._fi, int(fwd))
    GPIO.output(self._bi, int(back))

#    self._pca.setpwm(self._fi, 0, int(fwd * 4095.0))
#    self._pca.setpwm(self._bi, 0, int(back * 4095.0))
    self._pca.setpwm(self._si, 0, int(spd * 4095.0))

#--------------------------------------------------------
  def brake( self ):
    ''' Emergency stop by setting all values to 1. '''
    self._write((1.0, 1.0, 1.0))

#--------------------------------------------------------
  def speed( self, aSpeed ):
    ''' Set speed from -1.0 to 1.0 '''
    aSpeed *= wheel._scale

    if aSpeed < 0.0:
      v = (0.0, 1.0, wheel.clamp(-aSpeed))
    elif (aSpeed > 0):
      v = (1.0, 0.0, wheel.clamp(aSpeed))
    else:
      v = (0.0, 0.0, 0.0)

    self._write(v)

#--------------------------------------------------------
  def off( self ):
    ''' Turn the servo/led output signal off. '''
    self._pca.off(self._si)
