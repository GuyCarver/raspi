#!/usr/bin/env python3

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
  def __init__( self, pca, mx, si, fi, bi ):
    ''' Initialize the wheel with pca, multiplexer, pca pin for speed,
        and multiplexer pins for forward and back. '''

    super(wheel, self).__init__()

    self._pca = pca
    self._mx = mx
    self._si = si
    self._fi = fi
    self._bi = bi

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

    self._mx.write(self._fi, fwd)
    self._mx.write(self._bi, back)

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
      v = (0, 1, wheel.clamp(-aSpeed))
    elif (aSpeed > 0):
      v = (1, 0, wheel.clamp(aSpeed))
    else:
      v = (0, 0, 0.0)

    self._write(v)

#--------------------------------------------------------
  def off( self ):
    ''' Turn the servo/led output signal off. '''
    self._pca.off(self._si)
