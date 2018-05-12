#!/usr/bin/env python3

class part(object):
  """docstring for body"""

  @staticmethod
  def clamp( aValue, aMinMax ):
    return min(max(aValue, aMinMax[0]), aMinMax[1])

  def __init__(self, aServos, aIndex):
    self._servos = aServos
    self._index = aIndex
    self._value = 0.0
    self._targetvalue = 0.0
    self._rate = 0.0
    self._minmax = self._defminmax

  @property
  def minmax( self ):
    return self._minmax

  @minmax.setter
  def minmax( self, aValue ):
    if isinstance(aValue, tuple):
      self._minmax = aValue
    else:
      self._minmax = (max(-aValue, self._defminmax[0]), aValue)

  @property
  def rate( self ):
    return self._rate

  @rate.setter
  def rate( self, aValue ):
    self._rate = aValue

  def distance( self ):
    '''return distance from value to targetvalue.'''
    return self._targetvalue - self._value

  def settargetvalue( self, aValue ):
    '''Set the value clamped between min/max.'''
    self._targetvalue = part.clamp(aValue, self.minmax)
    #If no interp rate set value directly.
    if self._rate <= 0:
      self._value = self._targetvalue
      self.setservo()

  def off( self ):
    '''Turn the servo off.'''
    self._servos.off(self._index)

  def update( self, aDelta ):
    '''Update speed towards target given delta time in seconds.'''
    diff = self.distance()

    if diff != 0.0:
      #If no rate or diff too small just set directly.
      if (self._rate > 0.0) and (abs(diff) > 0.01):
        #Interpolate between src, target by delta.
        if diff < 0:
          mm = max
          aDelta *= -1.0
        else:
          mm = min

        diff = mm(self._rate * aDelta, diff)
        newvalue = self._value + diff
        self._value = mm(newvalue, self._targetvalue)
      else:
        self._value = self._targetvalue

      self.setservo()

class anglepart(part):
  '''Body part that uses and angle value from -90 to 90.'''
  def __init__( self, aServos, aIndex ):
    self._defminmax = (-90.0, 90.0)
    super(anglepart, self).__init__(aServos, aIndex)

  @property
  def curangle( self ): return self._value

  @property
  def angle( self ):
    return self._targetvalue

  @angle.setter
  def angle( self, aValue ):
    self.settargetvalue(aValue)

  def setservo( self ):
    '''Set the servo to current angle.'''
    self._servos.setangle(self._index, int(self._value))

class speedpart(part):
  '''Body part that uses a speed value from 0-100.'''
  def __init__( self, aServos, aIndex ):
    self._defminmax = (0.0, 100.0)
    super(speedpart, self).__init__(aServos, aIndex)

  @property
  def curspeed( self ): return self._value

  @property
  def speed( self ):
    return self._targetvalue

  @speed.setter
  def speed( self, aValue ):
    self.settargetvalue(aValue)

  def setservo( self ):
    '''Set the servo to current speed.'''
    self._servos.set(self._index, int(self._value))

if __name__ == '__main__':  #start server
  from pca9865 import *

  p = pca9865()
  a = anglepart(p, 14)
  mn, mx = a.minmax
  for x in range(1):
    for i in range(int(mn), int(mx), 1):
      a.angle = i
      sleep(0.01)
    for i in range(int(mx), int(mn), -1):
      a.angle = i
      sleep(0.01)
  a.off()

  s = speedpart(p, 15)
  mn, mx = s.minmax
  s.rate = 75.0

  def waitforit():
    while(s.distance()):
      sleep(0.01)
      s.update(0.01)

  s.speed = 100.0
  waitforit()
  s.speed = 0.0
  waitforit()
  print('done')
  s.off()

