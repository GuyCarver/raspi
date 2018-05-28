#!/usr/bin/env python3

# Controller for the quicrun 1060 Electronic Speed Control (ESP)

from time import sleep

#todo: May need to move speed values over time if the battery cannot handle it.

class quicrun(object):
  '''Controller for quicrun 1060 ESP.
     This controller works through the pca9865 servo controller.'''

#  _STOP = 40
#  _FORWARD_MAX = 58
#  _FORWARD_MIN = 42
#  _BACKWARD_MAX = 25
#  _BACKWARD_MIN = 38
#  _BACKWARD_INIT = 35

  _STOP = 50
  _FORWARD_MAX = 68
  _FORWARD_MIN = 52
  _BACKWARD_MAX = 30
  _BACKWARD_MIN = 48
  _BACKWARD_INIT = 45

  _defminmax = (-100.0, 100.0)

  @staticmethod
  def getperc( aMin, aMax, aPerc  ) :
    '''Interpolate between aMin and aMax by aPerc.
       Returns and integer value.'''
    return int((((aMax - aMin) * aPerc) // 100) + aMin)

  def __init__(self, aPCA, aIndex):
    '''aPCA = pca9865 object to use for PWM control of the ESC.
       aIndex = Servo index on pca9865 (0-15).
       If rate is > 0 then the speed value is interpolated over time.
       In this case update() must be called once per frame with delta time.
    '''
    super(quicrun, self).__init__()
    self._pca = aPCA
    self._index = aIndex
    self._rate = 0.0
    self._speed = 0.0
    self._scale = 1.0                           #Additional scaler used for temporary throttling.
    self._targetspeed = 0.0
    self._minmax = self._defminmax
    self.reset()

  @property
  def index( self ): return self._index

  @property
  def rate( self ):
    return self._rate

  @rate.setter
  def rate( self, aValue ):
    self._rate = aValue

  @property
  def scale( self ):
    return self._scale

  @scale.setter
  def scale( self, aValue ):
    self._scale = aValue

  @property
  def minmax( self ):
    return self._minmax

  @minmax.setter
  def minmax( self, aValue ):
    #If tuple just use directly without checking legitimate ranges.
    if isinstance(aValue, tuple):
      self._minmax = aValue
    else:
      #otherwise it's considered a single # we use for both min/max.
      self._minmax = (max(-aValue, self._defminmax[0]), aValue)

  @property
  def minspeed( self ): return self._minmax[0]

  @property
  def maxspeed( self ): return self._minmax[1]

  @property
  def minmaxforjson( self ):
    '''If min == -max then just return max (single value)
       otherwise return min/max tuple.'''
    if self._minmax[0] == -self._minmax[1]:
      return self._minmax[1]

    return self._minmax

  def clamp( self, aValue ):
    return min(max(aValue, self._minmax[0]), self._minmax[1])

  def reset( self ) :
    '''Need to send range of values to the ESP to initialize it.'''
#    self._set(75)
#    sleep(0.5)
#    self._set(100)
#    sleep(0.5)
    self._set(self._STOP)
    self._speed = 0.0
    self._prevspeed = 0.0
    self._targetspeed = 0.0

  def off( self ):
    '''Turn the esp off.'''
    self._pca.off(self._index)

  def _set( self, aValue ) :
    '''Set the ESP speed.'''
    self._pca.set(self._index, aValue)

  def _reverse( self ) :
    '''To reverse the ESP we have to go full stop, then backward, then stop again.
        After that, sending reverse values will actually reverse the motor.  If
        we dont do this, reverse values are just brakes.'''

    #Don't reverse unless previous speed was forward or stop.
    if self._prevspeed >= 0.0 :
      print('reversing')
      self._set(self._STOP)
      sleep(0.025)
      self._set(self._BACKWARD_INIT)
      sleep(0.025)
      self._set(self._STOP)
      sleep(0.015)

  def _setesp( self ) :
    '''Set the speed value on the esp.'''
    if self._speed == 0.0 :
      self._set(self._STOP)
    else:
      if self._speed > 0.0 :
        self._set(quicrun.getperc(self._FORWARD_MIN, self._FORWARD_MAX, self._speed))
      else:
        self._reverse()
        #100 + self._speed because we go backwards from backward min to backward max.
        self._set(quicrun.getperc(self._BACKWARD_MAX, self._BACKWARD_MIN, 100.0 + self._speed))

    self._prevspeed = self._speed

  @property
  def speed( self ):
    return self._targetspeed

  @speed.setter
  def speed( self, aValue ):
    #Set target speed and scale it based on the scale value.
    self._targetspeed = self.clamp(aValue) * self._scale
    #If rate is 0, we just set speed to target speed and send to ESP.
    #  This way update() doesn't need to be called.
    if self._rate == 0.0:
      self._speed = self._targetspeed
      self._setesp()

  def distance( self ):
    '''return distance from speed to targetspeed.'''
    return self._targetspeed - self._speed

  def update( self, aDelta ):
    '''Update speed towards target given delta time in seconds.'''
    diff = self.distance()

    if diff != 0.0:
      #If no rate or diff too small just set directly.
      if (self._rate > 0.0) and (abs(diff) > 0.01):
        #Interpolate between src, target by delta.
        if diff < 0.0:
          mm = max
          aDelta *= -1.0
        else:
          mm = min

        diff = mm(self._rate * aDelta, diff)
        newspeed = self._speed + diff
        self._speed = mm(newspeed, self._targetspeed)
      else:
        self._speed = self._targetspeed

      self._setesp()

#from pca9865 import *
#p = pca9865()
#q = quicrun(p, 8)
#q.speed = 0.0

if __name__ == '__main__':  #start server
  from pca9865 import *

  p = pca9865()
  q = quicrun(p, 8)
  q.rate = 10.0

  def waitforit():
    print(q.speed)
    while(q.distance()):
      sleep(0.01)
      q.update(0.01)

  q.speed = 25.0
  waitforit()
  q.speed = -25.0
  waitforit()
  q.speed = 5.0
  waitforit()
  q.speed = 0.0
  print('done.')
