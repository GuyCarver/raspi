#!/usr/bin/env python3

import RPi.GPIO as gp

#--------------------------------------------------------
class lightbank(object):
  """Control the bank of lights on the front of the tank with a single pin."""
  def __init__(self, aPin):
    super(lightbank, self).__init__()

    #Make sure gpio is initialized.
    if gp.getmode() != gp.BCM:
      gpioinit()

    gp.setup(aPin, gp.OUT)
    self._pin = aPin
    self._on = False
    self.on = False

#--------------------------------------------------------
  def __del__( self ):
    self.on = False

#--------------------------------------------------------
  @property
  def on( self ):
    return self._on

#--------------------------------------------------------
  @on.setter
  def on( self, aValue ):
    self._on = aValue
    gp.output(self._pin, self._on)

#--------------------------------------------------------
  def toggle( self ):
    ''' Toggle light on/off. '''
    self.on = not self.on

#--------------------------------------------------------
class strobe(object):
  '''Strobe 2 pins (labelled left/right) twice each repeatedly while on.
     assume gpio has been initialized to BCM mode.'''

  _DELAY = 0.05

#--------------------------------------------------------
  def __init__( self, left, right, delay = _DELAY ):
    '''left index, right index, delay in seconds (Default to _DELAY)'''
    super(strobe, self).__init__()
    self._lights = (left, right)
    self._time = 0.0
    self._index = 0
    gp.setup(left, gp.OUT)
    gp.setup(right, gp.OUT)
    self.on = False

#--------------------------------------------------------
  def __del__( self ):
    self.on = False

#--------------------------------------------------------
  @property
  def on( self ):
    return self._on

#--------------------------------------------------------
  @on.setter
  def on( self, aValue ):
    self._on = aValue
    if not aValue:                              # If turning off then turn off now instead of in update.
      for i in self._lights:
        gp.output(i, 0)
      self._index = 0
      self._time = 0.0

#--------------------------------------------------------
  def toggle( self ):
    ''' Toggle on/off. '''
    self.on = not self.on

#--------------------------------------------------------
  def update( self, aDT ):
    '''Call this once a frame with the elapsed time since last call.'''
    if self.on:
      self._time -= aDT
      if self._time <= 0.0:
        self._blink()

#--------------------------------------------------------
  def _blink( self ):
    '''Go to next blink state.'''
    self._time = strobe._DELAY
    side = (self._index >> 2) & 0x01
    self._index += 1
    gp.output(self._lights[side], (self._index & 1))

#--------------------------------------------------------
if __name__ == '__main__':
  gp.setwarnings(False)
  gp.setmode(gp.BCM)
  from time import sleep, perf_counter

  s = strobe(25, 8)
  l = lightbank(7)
  s.on = True
  prevtime = perf_counter()
  try:
    while 1:
      nexttime = perf_counter()
      delta = max(0.01, nexttime - prevtime)
      prevtime = nexttime
      l.on = int(nexttime) & 0x2
      s.update(delta)
      sleep(0.033)
  finally:
    s.on = False
