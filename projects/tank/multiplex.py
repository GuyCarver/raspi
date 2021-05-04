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
# FILE    multiplex.py
# BY      gcarver
# DATE    04/04/2021 10:57 AM
#----------------------------------------------------------------------

import RPi.GPIO as gp

#--------------------------------------------------------
class multiplex(object):
  ''' Driver for 74HC4067 16-Channel and 74HC4051 multiplexers '''

  OUT = gp.OUT
  IN = gp.IN
  PUP = gp.PUD_UP
  PDOWN = gp.PUD_DOWN

#--------------------------------------------------------
  def __init__( self, aPins, aSignal, aMode = IN, aPUD = PUP ):
    '''Initialize, aPins must be a container with gpio pin values, aSignal is the signal pin
        which will be set to aMode and aPUD (input mode only). '''
    super(multiplex, self).__init__()

    #Make sure gpio is initialized.
    if gp.getmode() != gp.BCM:
      gp.setwarnings(False)
      gp.setmode(gp.BCM)

    self._pins = aPins
    self._signal = aSignal
    self._max = 1 << len(aPins)                 # Maximum output index
    self._values = [0] * self._max              # value buffer
    self._mode = aMode

    for p in aPins:
      gp.setup(p, multiplex.OUT)

    if aMode == multiplex.OUT:
      gp.setup(aSignal, aMode)
    else:
      gp.setup(aSignal, aMode, aPUD)

#--------------------------------------------------------
  def _setIndex( self, aIndex ):
    ''' Set index to perform I/O on. '''
    for p in self._pins:
      gp.output(p, aIndex & 1)
      aIndex >>= 1

#--------------------------------------------------------
  def _write( self, aIndex ):
    ''' Write value to given index. '''

    self._setIndex(aIndex)
    gp.output(self._signal, self._values[aIndex])

#--------------------------------------------------------
  def write( self, aIndex, aValue ):
    ''' Write value to given index. Raise exception if not set for output. '''
    if self._mode != multiplex.OUT:
      raise Exception('Multiplexer not set for output.')
    if aIndex >= self._max:
      raise Exception('Index {} out of range {}'.format(aIndex, self._max - 1))

    self._values[aIndex] = aValue
    self._write(aIndex)

#--------------------------------------------------------
  def _read( self, aIndex ):
    ''' Read value from given index. '''
    self._setIndex(aIndex)
    self._values[aIndex] = gp.input(self._signal)

#--------------------------------------------------------
  def read( self, aIndex ):
    ''' Read value from given index. Raise exception if not set for input. '''
    if self._mode != multiplex.IN:
      raise Exception('Multiplexer not set for input.')
    if aIndex >= self._max:
      raise Exception('Index {} out of range {}'.format(aIndex, self._max - 1))

    self._read(aIndex)
    return self._values[aIndex]

#--------------------------------------------------------
  def value( self, aIndex ):
    ''' Read value from buffer that was set during update(). '''
    if self._mode != multiplex.IN:
      raise Exception('Multiplexer not set for input.')

    return self._values[aIndex]

#--------------------------------------------------------
  def setvalue( self, aIndex, aValue ):
    ''' Set value to buffer for write during update(). '''
    if self._mode != multiplex.OUT:
      raise Exception('Multiplexer no set for output.')

    self._values[aIndex] = aValue

#--------------------------------------------------------
  def update( self ):
    ''' Update by either reading data into or sending data from the buffer. '''

    fn = self._write if self._mode == multiplex.OUT else self._read
    for i in range(len(self._values)):
      fn(i)


if __name__ == '__main__':
  from time import sleep

  gpioinit()
  mx = multiplex((5,6,13,19), 26)
  while True:
    mx.update()
    print('vals:', mx.value(0), mx.value(1), '        ', end='\r')
    sleep(0.1)
