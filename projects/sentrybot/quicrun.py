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

  #States for reverse initialization over time.
  _REVERSE_INIT_1, _REVERSE_INIT_2, _REVERSE_INIT_3, _REVERSE = range(4)

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
    self._delay = 0.0                           #Delay value used for reverse init state changes.
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

  def _immediatereverse( self ):
    '''Perform immediate reverse action.  This causes a delay but is
       necessary if update loop isn't being used.'''
    self._set(self._STOP)
    sleep(0.03)
    self._set(self._BACKWARD_INIT)
    sleep(0.03)
    self._set(self._STOP)
    sleep(0.02)
    self._state = quicrun._REVERSE
    self._delay = 0.0

  def _reverse( self, aDelta ) :
    '''To reverse the ESP we have to go full stop, then backward, then stop again.
        After that, sending reverse values will actually reverse the motor.  If
        we dont do this, reverse values are just brakes.  This system uses 4 states
        that are updated over time to spread the reverse timing out over multiple
        frames. If aDelta is 0, immediate reverse is performed instead.'''

    #Don't reverse unless previous speed was forward or stop.
    if self._prevspeed >= 0.0 :
      #If no delta, we can't do reverse over time.  So do immediately.
      if aDelta <= 0.0:
        self._immediatereverse()
      else:
        #Start with reverse init1 state.
        self._state = quicrun._REVERSE_INIT_1
        self._delay = 0.03
        self._set(self._STOP)
        return                                    #Exit, don't set speed while in init1.
    else:
      self._delay -= aDelta
      if self._state == quicrun._REVERSE_INIT_1:
        #Stay in init 1 state until time is up.
        if self._delay <= 0.0:
          #Switch to init 2 state.
          self._state = quicrun._REVERSE_INIT_2
          self._delay = 0.03
          self._set(self._BACKWARD_INIT)
        return                                    #Exit, don't set speed while in init1 or 2.
      elif self._state == quicrun._REVERSE_INIT_2:
        #Stay in init 2 state until time is up.
        if self._delay <= 0.0:
          #Switch to init 3 state.
          self._state = quicrun._REVERSE_INIT_3
          self._delay = 0.02
          self._set(self._STOP)
        return                                    #Exit, don't set speed while in init2 or 3.
      elif self._state == quicrun._REVERSE_INIT_3:
        #Stay in init 3 state until time is up.
        if self._delay <= 0.0:
          #Switch to reverse state and fall through to speed setting.
          self._state = quicrun._REVERSE
        else:
          return                                  #Exit, don't set speed while in init3.

    #100 + self._speed because we go backwards from backward min to backward max.
    self._set(quicrun.getperc(self._BACKWARD_MAX, self._BACKWARD_MIN, 100.0 + self._speed))

  def _setesp( self, aDelta = 0.0 ) :
    '''Set the speed value on the esp. aDelta isnt needed if self._rate == 0.'''
    if self._speed == 0.0 :
      self._set(self._STOP)
    else:
      if self._speed >= 0.0 :
        self._set(quicrun.getperc(self._FORWARD_MIN, self._FORWARD_MAX, self._speed))
      else:
        self._reverse(aDelta)

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
          d = -aDelta
        else:
          mm = min
          d = aDelta

        diff = mm(self._rate * d, diff)
        newspeed = self._speed + diff
        self._speed = mm(newspeed, self._targetspeed)
      else:
        self._speed = self._targetspeed

    #update every call even if value hasn't changed because some state systems
    # (for reverse) require it.
    self._setesp(aDelta)

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
