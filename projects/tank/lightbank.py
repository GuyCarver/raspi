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
# FILE    lightsensor.py
# DATE    05/03/2021 11:31 AM
#----------------------------------------------------------------------

# Module for controlling bank of 12v LED lights using a light sensor connected to an
#  adc to control on/off state.

import adc
import RPi.GPIO as gp

class lightsensor(object):
  ''' Read a light sensor value from the adc and track on/of state. '''

  #--------------------------------------------------------
  #adc values
    _ADDRESS = 0x4A                             # Address is connected to SDA
    _MUX = 4                                    # This is the mux value to use to read light sensor data from adc
    _TRIGGER = 400                              # This is the threshold for turning headlights on
    _TRIGGERDELAY = 2.0                         # 2 seconds

  #--------------------------------------------------------
  def __init__( self ):
    super(lightsensor, self).__init__()
    self._adc = adc.create(lightsensor._ADDRESS)
    self._time = -1.0                            # Time in seconds until state change
    self._on = False
    self._value = 4095                          # Just start with a high number

  #--------------------------------------------------------
  @property
  def curvalue( self ):
    adc.read(self._adc, lightsensor._MUX)

  #--------------------------------------------------------
  @property
  def on( self ): return self._on

  #--------------------------------------------------------
  def update( self, aDT ):
    ''' Update the light sensor and change state if state change lasted long enough.
        Returns true if on/off state changed.
    '''

    bchange = False

    self._value = self.curvalue                 # Get the newest data
    on = self._value < lightsensor._TRIGGER
    # Check if switching trigger state.
    if on != self._on:
      if self._time > 0.0:                      # If delay time is on then dec it
        self._time -= aDT
        if self._time <= 0.0:                   # If time is up change state
          self._on = on
          bchange = True
      else:
        self._time = lightsensor._TRIGGERDELAY  # Start the timer
    else:
      self._time = -1.0                         # Make sure timer is reset

    return bchange

#--------------------------------------------------------
class lightbank(object):
  ''' Control the bank of lights on the front of the tank with a single pin. '''

  #--------------------------------------------------------
  def __init__(self, aPin):
    super(lightbank, self).__init__()

    #Make sure gpio is initialized.
    if gp.getmode() != gp.BCM:
      gp.setwarnings(False)
      gp.setmode(gp.BCM)

    gp.setup(aPin, gp.OUT)
    self._pin = aPin
    self._on = False
    self.on = False

    self._sensor = lightsensor()

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
    if aValue:
      self._sensor._on = True                   # Set sensor state to reflect light on state

  #--------------------------------------------------------
  def toggle( self ):
    ''' Toggle light on/off. '''
    self.on = not self.on

  #--------------------------------------------------------
  def update( self, aDT ):
    ''' aDT = delta time in seconds. Control light on/off with sensor. '''
    if self._on:
      if self._sensor.update(aDT):
        gp.output(self._pin, self._sensor.on)

#--------------------------------------------------------
if __name__ == '__main__':
  from time import sleep, perf_counter

  l = lightbank(7)
  l.on = True
  prevtime = perf_counter()
  try:
    while 1:
      nexttime = perf_counter()
      delta = max(0.01, nexttime - prevtime)
      prevtime = nexttime
      l.update(delta)
      sleep(0.033)
  finally:
    l.on = False
