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
  def __init__( self, pca, si, fi, bi ):
    ''' Initialize the wheel with pca, speed, forward and back indexes. '''
    super(wheel, self).__init__()

    self._pca = pca
    self._si = si
    self._fi = fi
    self._bi = bi
    self.speed(0.0)

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
    f, b, s = aValues

    self._pca.Set(self._fi, f)
    self._pca.Set(self._bi, b)
    self._pca.Set(self._si, s)

#--------------------------------------------------------
  def brake( self ):
    ''' Emergency stop by setting all values to 1. '''
    v = (1.0, 1.0, 1.0)
    self._write

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
    self._pca.Off(self._si)
