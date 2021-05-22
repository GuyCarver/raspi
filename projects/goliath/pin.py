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
# FILE    pin.py
# DATE    04/29/2021 08:53 AM
#----------------------------------------------------------------------

import RPi.GPIO as gp

#--------------------------------------------------------
class pin(object):
  ''' Wrap gpio pin into object. Use the value property to set/get the value.
       Make sure to get only input pins and set output pins.
  '''

  IN = gp.IN
  OUT = gp.OUT
  PUP = gp.PUD_UP
  PDOWN = gp.PUD_DOWN

  #--------------------------------------------------------
  def __init__( self, aIndex, aMode = OUT, aUD = PUP ):
    super(pin, self).__init__()
    self._pin = aIndex
    self._mode = aMode
    self._value = 0

    if gp.getmode() != gp.BCM:
      gp.setwarnings(False)
      gp.setmode(gp.BCM)

    if aMode == pin.IN:
      gp.setup(self._pin, aMode, aUD)
    else:
      gp.setup(self._pin, aMode)

  #--------------------------------------------------------
  @property
  def value( self ):
    #If input pin then read value.  Otherwise just return the set value.
    if self._mode == pin.IN:
      self._value = gp.input(self._pin)
    return self._value

  #--------------------------------------------------------
  @value.setter
  def value( self, aValue ):
    #Only do something if output pin.
    if self._mode == pin.OUT:
      gp.output(self._pin, aValue)
      self._value = aValue

#--------------------------------------------------------
class muxpin(object):
  ''' Wrap multiplexer and index into single object. Use the value property to set/get
       the value.  Make sure to get only input pins and set output pins.  The type is
       determined by the Multiplexer type which is set to either input or output.
  '''

  #--------------------------------------------------------
  def __init__( self, aMultiplexer, aIndex ):
    super(muxpin, self).__init__()
    self._mux = aMultiplexer
    self._pin = aIndex

  #--------------------------------------------------------
  @property
  def value( self ):
    if self._mux.isin:
      self._value = self._mux.read(self._pin)
    return self._value

  #--------------------------------------------------------
  @value.setter
  def value( self, aValue ):
    ''' Write given value 0/1 to multiplexer using immediate mode. '''
    if self._mux.isout:
      self._mux.write(self._pin, aValue)
      self._value = aValue
