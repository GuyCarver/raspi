#!/usr/bin/env python3
#11/10/2018 02:20 PM

class atom(object):
  '''Controller for Novak Atom ESC.'''
  _defminmax = (94.0, 120.0)

  def __init__( self, aPCA, aIndex, aName = '' ):
    '''aPCA = pca9685 object to use for PWM control of the ESC.
       aIndex = Servo index on pca9685 (0-15).
       If rate is > 0 then the speed value is interpolated over time.
       In this case update() must be called once per frame with delta time.
    '''
    super(atom, self).__init__()
    self._pca = aPCA
    self._index = aIndex
    self._minmax = atom._defminmax
    self._name = aName
    self._rate = 0.0
    self.reset()

  @property
  def index( self ): return self._index

  def off( self ):
    '''Turn the ESP off.'''
    self._pca.off(self._index)

  def _set( self, aValue ) :
    '''Set the ESP speed.'''
    self._pca.set(self._index, aValue)

  #Center property does nothing, it's here for body part interface compat.
  @property
  def center( self ):
    return 0.0

  @center.setter
  def center( self, aValue ):
    pass

  @property
  def minmax( self ):
    return self._minmax

  @minmax.setter
  def minmax( self, aValue ):
     #If tuple just use directly without checking legitimate ranges.
    if isinstance(aValue, tuple) or isinstance(aValue, list):
      self._minmax = aValue
    else:
      #otherwise it's considered a single # we use for both min/max.
      self._minmax = (max(-aValue, self._defminmax[0]), aValue)

  @property
  def minmaxforjson( self ):
    '''If min == -max then just return max (single value)
       otherwise return min/max tuple.'''
    if self._minmax[0] == -self._minmax[1]:
      return self._minmax[1]

    return self._minmax

  @property
  def name( self ):
    return self._name

  @property
  def rate( self ):
    return self._rate

  @rate.setter
  def rate( self, aValue ):
    self._rate = aValue

  @property
  def speed( self ):
    return self._targetspeed

  @speed.setter
  def speed( self, aValue ):
    self._targetspeed = self.clamp(aValue)
    #If rate is 0, we just set speed to target speed and send to ESP.
    #  This way update() doesn't need to be called.
    if self._rate == 0.0:
      self._speed = self._targetspeed

  def clamp( self, aValue ):
    return min(max(aValue, self._minmax[0]), self._minmax[1])

  def distance( self ):
    '''return distance from speed to targetspeed.'''
    return self._targetspeed - self._speed

  def reset( self ) :
    self._speed = self._minmax[0]
    self._targetspeed = self._speed

  def update( self, aDelta ):
    '''Update speed towards target given delta time in seconds.'''
    diff = self.distance()

    if diff != 0.0:
      #If no rate or diff too small just set directly.
      if (self._rate > 0.0) and (abs(diff) > 0.01):
        #Interpolate between src, target by delta.
        if diff < 0.0:
          mm = max
          d = -aDelta
        else:
          mm = min
          d = aDelta

        diff = mm(self._rate * d, diff)
        newspeed = self._speed + diff
        self._speed = mm(newspeed, self._targetspeed)
      else:
        self._speed = self._targetspeed

    self._set(self._speed)

if __name__ == '__main__':  #start server
  from pca9685 import *

  p = pca9685(100)
  a = atom(p, 15)
  a.rate = 10.0

  def waitforit():
    print(a.speed)
    while(a.distance()):
      sleep(0.01)
      a.update(0.01)

  a.speed = 0.0
  waitforit()
  a.speed = 150.0
  waitforit()
  a.speed = 100.0
  waitforit()
  a.speed = 50.0
  waitforit()
  a.speed = 0.0
  print('done.')
