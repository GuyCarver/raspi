#!/usr/bin/env python3

#----------------------------------------------------------------------
# Copyright (c) 2021, gcarver
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#
#     * The name of Guy Carver may not be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# FILE    esc.py
# DATE    04/26/2021 09:25 AM
#----------------------------------------------------------------------

# Controller for brushless motor escs
# Many escs require an initialization process setting min/max/center before use.
#  the min/max/center pwm values also vary by esc model.
# This module also contains subclasses with ranges for the suprass 60a esc and quicrun esc.

from time import sleep

#--------------------------------------------------------
class esc(object):
  ''' Controller for a brushless motor esc.
      This controller works through the pca9685 servo controller.
      Converts speed values -1.0 to 1.0 into PWM signal values required to reflect that
      speed on the esc.
  '''

  #Default ranges.
  _IDLE, _FWD_MIN, _FWD_MAX, _BACK_MIN, _BACK_MAX = range(5)

  #States
  _STOPPED, _FORWARD, _REVERSE, _REVERSE_INIT1, _REVERSE_INIT2 = range(5)

  _DEFMINMAX = (-1.0, 1.0)                      # Minimum/Maximum values for speed settings.

  #--------------------------------------------------------
  @staticmethod
  def getinterp( aMin, aMax, aValue ) :
    ''' Interpolate between aMin and aMax by aValue 0.0-1.0. '''
    return ((aMax - aMin) * aValue) + aMin

  #--------------------------------------------------------
  def __init__(self, aPCA, aIndex, aRanges, aName = ''):
    '''aPCA = pca9685 object to use for PWM control of the ESC.
       aIndex = Servo index on pca9685 (0-15).
       aRanges = tuple of 5 range values idle, fwdmin, fwdmax, backmin, backmax
    '''
    super(esc, self).__init__()
    self._initdelay = 0.2
    self._revdelays = (0.03, 0.03)
    self._pca = aPCA
    self._index = aIndex
    self._name = aName
    self._ranges = aRanges
    self._rate = 0.0                            #Rate in units per second change allowed.
    self._delay = 0.0                           #Delay value used for reverse init state changes.
    self._speed = 0.0                           #Speed value between -1.0 and 1.0.
    self._scale = 1.0                           #Additional scaler used for temporary throttling.
    self._targetspeed = 0.0
    self._minmax = esc._DEFMINMAX
    self._state = esc._STOPPED
    self.reset()

  #--------------------------------------------------------
  @property
  def index( self ): return self._index

  #--------------------------------------------------------
  @property
  def name( self ): return self._name

  #--------------------------------------------------------
  @property
  def rate( self ):
    return self._rate

  @rate.setter
  def rate( self, aValue ):
    '''Set rate in units/second for update.'''
    self._rate = aValue

  #--------------------------------------------------------
  @property
  def scale( self ):
    return self._scale

  @scale.setter
  def scale( self, aValue ):
    self._scale = aValue

  #--------------------------------------------------------
  @property
  def minmax( self ):
    return self._minmax

  @minmax.setter
  def minmax( self, aValue ):
    '''Set min/maximum speed values between -1.0 and 1.0'''

    #If tuple just use directly without checking legitimate ranges.
    if isinstance(aValue, tuple) or isinstance(aValue, list):
      self._minmax = aValue
    else:
      #otherwise it's considered a single # we use for both min/max.
      self._minmax = (max(-aValue, self._defminmax[0]), aValue)

  #--------------------------------------------------------
  @property
  def minspeed( self ): return self._minmax[0]

  #--------------------------------------------------------
  @property
  def maxspeed( self ): return self._minmax[1]

  #--------------------------------------------------------
  @property
  def minmaxforjson( self ):
    '''If min == -max then just return max (single value)
       otherwise return min/max tuple.'''
    if self._minmax[0] == -self._minmax[1]:
      return self._minmax[1]

    return self._minmax

  #--------------------------------------------------------
  def range( self, aIndex ):
    ''' Get range value given the range index. '''
    return self._ranges[aIndex]

  #--------------------------------------------------------
  def clamp( self, aValue ):
    return min(max(aValue, self._minmax[0]), self._minmax[1])

  #--------------------------------------------------------
  def reset( self ) :
    self._set(self.range(esc._FWD_MAX))
    sleep(self._initdelay)
    self._set(self.range(esc._BACK_MAX))
    sleep(self._initdelay)
    self._set(self.range(esc._IDLE))
    sleep(self._initdelay)
    self._speed = 0.0
    self._targetspeed = self._speed

  #--------------------------------------------------------
  def off( self ):
    '''Turn the ESP off.'''
    self._pca.off(self._index)

  #--------------------------------------------------------
  def _set( self, aValue ) :
    '''Set the ESP speed.'''
#     print('setting:', aValue)
    self._pca.set(self._index, aValue)

  #--------------------------------------------------------
  #Center property does nothing, it's here for body part interface compat.
  @property
  def center( self ):
    return self.range(esc._IDLE)

  @center.setter
  def center( self, aValue ):
    pass

  #--------------------------------------------------------
  #The value property is for compatability with the body parts interface for the animation system.
  @property
  def value( self ):
    return self.speed

  @value.setter
  def value( self, aValue ):
    self.speed = aValue

  #--------------------------------------------------------
  @property
  def speed( self ):
    return self._targetspeed

  @speed.setter
  def speed( self, aValue ):
    '''Set target speed -1.0 to 1.0 and scale it based on the scale value.'''

    self._targetspeed = self.clamp(aValue) * self._scale
    #If rate is 0, we just set speed to target speed and send to ESP.
    #  This way update() doesn't need to be called.
    if self._rate == 0.0:
      self._speed = self._targetspeed
      self._updatestate()

  #--------------------------------------------------------
  @property
  def distance( self ):
    '''return distance from speed to targetspeed.'''
    return self._targetspeed - self._speed

  #--------------------------------------------------------
  def _checkstop( self ):
    '''  '''
    if self._speed == 0.0:
      self._state = esc._STOPPED
      self._set(self.range(esc._IDLE))
      return True
    return False

  #--------------------------------------------------------
  def _checkforward( self ):
    '''  '''
    if self._speed > 0.0:
      self._state = esc._FORWARD
      return True
    return False

  #--------------------------------------------------------
  def _checkreverse( self, aDelta ) :
    ''' Check if we wish to go in reverse, if so we must initialize reverse through
        2 phases.
    '''

    if self._speed < 0.0:
      if aDelta <= 0.0:
#         print('no delta')
        self._state = esc._REVERSE
      else:
        #Start 1st phase of reverse init by setting minimum reverse.
        self._set(self._ranges[esc._BACK_MIN])
        self._state = esc._REVERSE_INIT1
        self._delay = self._revdelays[0]
      return True

    return False

  #--------------------------------------------------------
  def ud_stopped( self, aDelta ):
    '''Does nothing but look for forward/reverse state changes.'''
    if not self._checkreverse(aDelta):
      self._checkforward()
    return

  #--------------------------------------------------------
  def stop( self ):
    '''Immediately stop the device'''
    self._speed = self._targetspeed = 0.0
    self._checkstop()

  #--------------------------------------------------------
  def ud_forward( self, aDelta ):
    '''Update speed and look for reverse/stopped state changes.'''
    self._set(esc.getinterp(self.range(esc._FWD_MIN), self.range(esc._FWD_MAX), self._speed))
    if not self._checkstop():
      self._checkreverse(aDelta)

  #--------------------------------------------------------
  def ud_reverse( self, aArg ):
    '''In reverse.  Look to go to forward or stop.'''
    self._set(esc.getinterp(self.range(esc._BACK_MAX), self.range(esc._BACK_MIN), 1.0 + self._speed))
    if not self._checkstop():
      self._checkforward()

#--------------------------------------------------------
  def ud_reverse1( self, aDelta ):
    '''1st of 4 braking states.  This is set to stop, and waits to set reverse2.'''
    #If no delta, we can't do reverse over time.  So do immediately.
#     print('udr2')
    self._delay -= aDelta
    #Stay in init 1 state until time is up.
    if self._delay <= 0.0:
      self._set(self._ranges[esc._IDLE])
      self._state = esc._REVERSE_INIT2
      self._delay = self._revdelays[1]

    #Look for forward or stop state changes.
    if not self._checkstop():
      self._checkforward()

#--------------------------------------------------------
  def ud_reverse2( self, aDelta ):
    '''1st of 4 braking states.  This is set to stop, and waits to set reverse2.'''
    #If no delta, we can't do reverse over time.  So do immediately.
#     print('udr3')
    self._delay -= aDelta
    #Stay in init 1 state until time is up.
    if self._delay <= 0.0:
      self._state = esc._REVERSE

    #Look for forward or stop state changes.
    if not self._checkstop():
      self._checkforward()

  #--------------------------------------------------------
  _STATEFUNCS = (ud_stopped, ud_forward, ud_reverse, ud_reverse1, ud_reverse2)

  #--------------------------------------------------------
  def _updatestate( self, aDelta = 0.0 ) :
    '''Update based on the current state.'''
    #Get the state function and call it.
    esc._STATEFUNCS[self._state](self, aDelta)

  #--------------------------------------------------------
  def update( self, aDelta ):
    '''Update speed towards target given delta time in seconds.'''
    diff = self.distance

    if diff != 0.0:
      #If no rate or diff too small just set directly.
      if (self._rate > 0.0) and (abs(diff) > 0.001):
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

#--------------------------------------------------------
class surpass(esc):
  ''' Controller for surpass 60a ESC. '''

  #idle, fwdmin, fwdmax, backmin, backmax
  _RANGES = (0.60, 0.66, 1.0, 0.54, 0.15)

  #--------------------------------------------------------
  def __init__( self, aPCA, aIndex, aName = '' ):
    super(surpass, self).__init__(aPCA, aIndex, surpass._RANGES, aName)
    self._revdelays = (0.25, 0.03)  #The surpass esc has longer delay for 1st phase of reverse init.

#--------------------------------------------------------
class quicrun(esc):
  ''' Controller for quicrun 1060 ESC. '''

  #idle, fwdmin, fwdmax, backmin, backmax
  _RANGES = (0.76, 0.78, 1.0, 0.74, 0.5)

  #--------------------------------------------------------
  def __init__( self, aPCA, aIndex, aName = '' ):
    super(quicrun, self).__init__(aPCA, aIndex, quicrun._RANGES, aName)

#--------------------------------------------------------
# if __name__ == '__main__':  #start server
#   import pca9685 as pca
#
#   pca.startup()
#   e = surpass(pca, 15, 'test')
#   e.rate = 1.0
#
#   def waitforit():
#     print(e.speed)
#     while(e.distance):
#       sleep(0.01)
#       e.update(0.01)
#
#   e.speed = 1.0
#   waitforit()
#   e.speed = -1.0
#   waitforit()
#   e.speed = 0.5
#   waitforit()
#   e.speed = 0.0
#   waitforit()
#   print('done.')

if __name__ == '__main__':
  import pca9685 as pca
  from time import sleep

  pca.startup()
  e = surpass(pca, 15, 'test')
  e.rate = 100.0

  def waitforit(delay):
    print(e.speed)
    while(e.distance or (delay > 0.0)):
      e.update(0.01)
      sleep(0.01)
      delay -= 0.01

  def ss( a, d ):
    e.speed = a
    waitforit(d)

  ss(0.10, 2.0)
  ss(-0.5, 3.0)
  ss(0.0, 1.0)
  e.off()
  print('done.')
