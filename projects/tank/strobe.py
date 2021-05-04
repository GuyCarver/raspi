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
# FILE    strobe.py
# BY      gcarver
# DATE    05/04/2021 01:50 AM
#----------------------------------------------------------------------

import RPi.GPIO as gp

#--------------------------------------------------------
class strobe(object):
  '''Strobe 2 pins (labelled left/right) twice each repeatedly while on.
     assume gpio has been initialized to BCM mode.'''

  _DELAY = 0.05

  #--------------------------------------------------------
  def __init__( self, left, right, delay = _DELAY ):
    '''left index, right index, delay in seconds (Default to _DELAY)'''
    super(strobe, self).__init__()

    #Make sure gpio is initialized.
    if gp.getmode() != gp.BCM:
      gp.setwarnings(False)
      gp.setmode(gp.BCM)

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
  from time import sleep, perf_counter

  s = strobe(25, 8)
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
