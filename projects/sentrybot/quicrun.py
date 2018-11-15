#!/usr/bin/env python3

# Controller for the quicrun 1060 Electronic Speed Control (ESP)

from time import sleep
from os import environ

class quicrun(object):
  '''Controller for quicrun 1060 ESP.
     This controller works through the pca9865 servo controller.'''

  if 'GUY' in environ:
    _IDLE = 40
    _FORWARD_MAX = 58
    _FORWARD_MIN = 42
    _BACKWARD_MAX = 25
    _BACKWARD_MIN = 38
    _BACKWARD_INIT = 35
  else:
    _IDLE = 50
    _FORWARD_MAX = 68
    _FORWARD_MIN = 52
    _BACKWARD_MAX = 30
    _BACKWARD_MIN = 48
    _BACKWARD_INIT = 45

  #States
  _STOPPED, _BRAKING, _FORWARD, _REVERSE_INIT_1, _REVERSE_INIT_2, _REVERSE_INIT_3, _REVERSE = range(7)

  _defminmax = (-100.0, 100.0)

  @staticmethod
  def getperc( aMin, aMax, aPerc  ) :
    '''Interpolate between aMin and aMax by aPerc.
       Returns and integer value.'''
    return int((((aMax - aMin) * aPerc) // 100) + aMin)

  def __init__(self, aPCA, aIndex, aName):
    '''aPCA = pca9865 object to use for PWM control of the ESC.
       aIndex = Servo index on pca9865 (0-15).
       If rate is > 0 then the speed value is interpolated over time.
       In this case update() must be called once per frame with delta time.
    '''
    super(quicrun, self).__init__()
    self._pca = aPCA
    self._index = aIndex
    self._name = aName
    self._rate = 0.0
    self._delay = 0.0                           #Delay value used for reverse init state changes.
    self._speed = 0.0
    self._scale = 1.0                           #Additional scaler used for temporary throttling.
    self._targetspeed = 0.0
    self._minmax = quicrun._defminmax
    self._state = quicrun._STOPPED
    self.reset()

  @property
  def index( self ): return self._index

  @property
  def name( self ): return self._name

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
    if isinstance(aValue, tuple) or isinstance(aValue, list):
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
#    self._set(75)
#    sleep(0.5)
#    self._set(100)
#    sleep(0.5)
    self._set(quicrun._IDLE)
    self._speed = 0.0
    self._targetspeed = self._speed

  def off( self ):
    '''Turn the ESP off.'''
    self._pca.off(self._index)

  def _set( self, aValue ) :
    '''Set the ESP speed.'''
    self._pca.set(self._index, aValue)

  def _immediatereverse( self ):
    '''Perform immediate reverse action.  This causes a delay but is
       necessary if update loop isn't being used.'''
    self._set(quicrun._IDLE)
    sleep(0.03)
    self._set(quicrun._BACKWARD_INIT)
    sleep(0.03)
    self._set(quicrun._IDLE)
    sleep(0.02)
    self._state = quicrun._REVERSE
    self._delay = 0.0

  #Center property does nothing, it's here for body part interface compat.
  @property
  def center( self ):
    return 0.0

  @center.setter
  def center( self, aValue ):
    pass

  #The value property is for compatability with the body parts interface for the animation system.
  @property
  def value( self ):
    return self.speed

  @value.setter
  def value( self, aValue ):
    self.speed = aValue

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
      self._updatestate()

  def distance( self ):
    '''return distance from speed to targetspeed.'''
    return self._targetspeed - self._speed

  def brake( self, abTF ):
    '''Full immediate stop.  Enter braking state and stay there until told to exit.'''
    if abTF:
      if self._state != quicrun._BRAKING:
        self._state = quicrun._BRAKING
        if self._speed >= 0.0:
          self._set(quicrun._BACKWARD_MAX)
          self._delay = 2.0                      #Maximum brake time is 2 seconds before we go to idle.
        else:
          self._delay = 0.0                      #If reverse we can't brake so just come to stop.
        self._speed = self._targetspeed = 0.0
      else:
        self._delay = 2.0                        #Re-apply brake time.
    else:
      if self._state == quicrun._BRAKING:
        self._state = quicrun._STOPPED

  def _checkstop( self ):
    '''  '''
    if self._speed == 0.0:
      self._state = quicrun._STOPPED
      self._set(quicrun._IDLE)
      return True
    return False

  def _checkforward( self ):
    '''  '''
    if self._speed > 0.0:
      self._state = quicrun._FORWARD
      return True
    return False

  def _checkreverse( self, aDelta ) :
    '''To reverse the ESP we have to go full stop, then backward, then stop again.
        After that, sending reverse values will actually reverse the motor.  If
        we dont do this, reverse values are just brakes.  This system uses 4 states
        that are updated over time to spread the reverse timing out over multiple
        frames. If aDelta is 0, immediate reverse is performed instead.'''

    if self._speed < 0.0:
      #If no delta, we can't do reverse over time.  So do immediately.
      if aDelta <= 0.0:
        self._immediatereverse()
      else:
        #Start with reverse init1 state.
        self._state = quicrun._REVERSE_INIT_1
        self._delay = 0.03
        self._set(quicrun._IDLE)
      return True

    return False

  def ud_stopped( self, aDelta ):
    '''Does nothing but look for forward/revurse state changes.'''
    if not self._checkreverse(aDelta):
      self._checkforward()
    return

  def ud_forward( self, aDelta ):
    '''Update speed and look for reverse/stopped state changes.'''
    self._set(quicrun.getperc(quicrun._FORWARD_MIN, quicrun._FORWARD_MAX, self._speed))
    if not self._checkstop():
      self._checkreverse(aDelta)

  def ud_braking( self, aDelta ):
    '''In braking state.  Wait until done then revert to stopped.'''
    self._delay -= aDelta
    #Stay in init 1 state until time is up.
    if self._delay <= 0.0:
      self._set(quicrun._IDLE)

  def ud_reverse1( self, aDelta ):
    '''1st of 4 braking states.  This is set to stop, and waits to set reverse2.'''
    #If no delta, we can't do reverse over time.  So do immediately.
    self._delay -= aDelta
    #Stay in init 1 state until time is up.
    if self._delay <= 0.0:
      #Switch to init 2 state.
      self._state = quicrun._REVERSE_INIT_2
      self._delay = 0.03
      self._set(quicrun._BACKWARD_INIT)

    #Look for forward or stop state changes.
    if not self._checkstop():
      self._checkforward()

  def ud_reverse2( self, aDelta ):
    '''Phase 2, speed set to _BACKWARD_INIT. Wait to set reverse3.'''
    #Stay in init 2 state until time is up.
    self._delay -= aDelta

    if self._delay <= 0.0:
      #Switch to init 3 state.
      self._state = quicrun._REVERSE_INIT_3
      self._delay = 0.02
      self._set(quicrun._IDLE)

    #Look for forward or stop state changes.
    if not self._checkstop():
      self._checkforward()

  def ud_reverse3( self, aDelta ):
    '''Phase 3, speed set to _IDLE.  Wait to go in reverse.'''
    #Stay in init 3 state until time is up.
    self._delay -= aDelta

    if self._delay <= 0.0:
      #Switch to reverse state.
      self._state = quicrun._REVERSE

    #Look for forward or stop state changes.
    if not self._checkstop():
      self._checkforward()

  def ud_reverse( self, aArg ):
    '''In reverse.  Look to go to forward or stop.'''
    self._set(quicrun.getperc(quicrun._BACKWARD_MAX, quicrun._BACKWARD_MIN, 100.0 + self._speed))
    if not self._checkstop():
      self._checkforward()

  _STATEFUNCS = (ud_stopped, ud_braking, ud_forward, ud_reverse1, ud_reverse2, ud_reverse3, ud_reverse)

  def _updatestate( self, aDelta = 0.0 ) :
    '''Update based on the current state.'''
    #Get the state function and call it.
    quicrun._STATEFUNCS[self._state](self, aDelta)

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

    self._updatestate(aDelta)                   #Update the state system.

#from pca9865 import *
#p = pca9865()
#q = quicrun(p, 8)
#q.speed = 0.0

if __name__ == '__main__':  #start server
  from pca9865 import *

  p = pca9865()
  q = quicrun(p, 8, 'test')
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
