#!/usr/bin/env python3

#--------------------------------------------------------
class wheel(object):
  ''' Control wheel motor controller '''

  _MINSPEED = .2
#   _MAXSPEED = 1.0
  _SPEEDRANGE = 1.0 - _MINSPEED

  #--------------------------------------------------------
  def __init__( self, pca, si, bi ):
    ''' Initialize the wheel with pca, speed, forward and back indexes.
        si is a pca index, bi is Pin objects (see pin.py). '''
    super(wheel, self).__init__()

    self._pca = pca
    self._si = si
    self._bi = bi
    self._name = ''
    self.speed = 0.0

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
  @property
  def speed( self ):
    return self._speed

  #--------------------------------------------------------
  @speed.setter
  def speed( self, aValue ):
    ''' Set speed from -1.0 to 1.0 '''

    self._speed = aValue

    if aValue < 0.0:
      v = (1, -wheel.clamp(aValue))
    elif (aValue > 0):
      v = (0, wheel.clamp(aValue))
    else:
      v = (0, 0.0)

    self._write(v)

  #--------------------------------------------------------
  @classmethod
  def clamp( cls, aValue ) :
    ''' Convert float aValue to value between min and max speed. '''
    return (min(1.0, aValue) * wheel._SPEEDRANGE) + wheel._MINSPEED

  #--------------------------------------------------------
  def _write( self, aValues ):
    ''' Write data to the pca. '''
    back, spd = aValues

    #Set full range of PWM signal to get a value from 0 to 1 on the pin.
#     print(fwd, back, spd)
    self._bi.value = back
    self._pca.setpwm(self._si, spd) #Set pwm to % 0.0-1.0

  #--------------------------------------------------------
  def brake( self ):
    ''' Emergency stop by setting all values to 1. '''
    self._write(1, 1.0)
    self._write(0, 1.0)

  #--------------------------------------------------------
  def off( self ):
    ''' Turn the servo/led output signal off. '''
    self._pca.off(self._si)

