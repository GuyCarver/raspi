#!/usr/bin/env python3

class strobe(object):
  '''Strobe 2 pca indexes (labelled left/right) twice each repeatedly while on.'''

  _DELAY = 0.05

  def __init__( self, pca, left, right, delay = _DELAY ):
    '''pca module, left index, right index, delay in seconds (Default to _DELAY)'''
    super(strobe, self).__init__()
    self._pca = pca
    self._lights = (left, right)
    self._time = 0.0
    self._index = 0
    self.on = False

  def __del__( self ):
    self.on = False

  @property
  def on( self ):
    return self._on

  @on.setter
  def on( self, aValue ):
    self._on = aValue
    if not aValue:
      for i in self._lights:
        self._pca.Set(i, 0.0)
      self._index = 0
      self._time = 0.0

  def update( self, aDT ):
    '''Call this once a frame with the elapsed time since last call.'''
    if self.on:
      self._time -= aDT
      if self._time <= 0.0:
        self._blink()

  def _blink( self ):
    '''Go to next blink state.'''
    self._time = strobe._DELAY
    side = (self._index >> 2) & 0x01
    self._index += 1
    self._pca.Set(self._lights[side], 1.0 if (self._index & 1) else 0.0)

if __name__ == '__main__':
  import pca
  from time import sleep, perf_counter
  pca.Startup()
  pca.Set(0, 1.0)
  pca.Set(1, 1.0)
  pca.Set(2, 1.0)
  pca.Set(3, 1.0)
  s = strobe(pca, 15, 14)
  s.on = True
  prevtime = perf_counter()
  try:
    while 1:
      nexttime = perf_counter()
      delta = max(0.01, nexttime - prevtime)
      prevtime = nexttime
      s.update(delta)
      sleep(0.033)
  finally:
    s.on = False
