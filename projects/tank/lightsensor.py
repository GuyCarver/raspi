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

#Module for reading/tracking light sensor data  and reporting status.

import adc

class lightsensor(object):
  '''docstring for lightsensor'''

  #--------------------------------------------------------
  #adc
    _ADDRESS = 0x4A                             # Address is connected to SDA.
    _MUX = 4                                    # This is the mux value to use to read light sensor data from adc.
    _TRIGGER = 400                              # This is the threshold for turning headlights on.
    _TRIGGERDELAY = 2.0                         # 2 seconds.

  #--------------------------------------------------------
  def __init__( self ):
    super(lightsensor, self).__init__()
    self._adc = adc.create(lightsensor._ADDRESS)
    self._time = 0
    self._off = False
    self._value = self.curvalue

  #--------------------------------------------------------
  @property
  def curvalue( self ):
    adc.read(self._adc, lightsensor._MUX)


  def update( self, aDT ):
    '''  '''
    #todo: Get the newest data.
    # Check if switching trigger state.
