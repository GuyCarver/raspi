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
# FILE    camera.py
# DATE    04/13/2021 10:33 PM
#----------------------------------------------------------------------

#--------------------------------------------------------
class camera(object):
  '''docstring for camera'''

  _PANRANGE = (-75.0, 12.0, 110.0)  #right/center/left
  _TILTRANGE = (-90.0, -10.0, 30.0) #up/center/down
  _DEFAULTRATE = 2.0                            # v/second movement rate

  #--------------------------------------------------------
  def __init__( self, aPCA, aPanPin, aTiltPin ):
    super(camera, self).__init__()
    self._panPin = aPanPin
    self._tiltPin = aTiltPin
    self._pca = aPCA
    self._pan = 0.0
    self._tilt = 0.0
    self._rate = camera._DEFAULTRATE
    self.update(0.0, 0.0, 0.0)

  #--------------------------------------------------------
  def center( self ):
    '''  '''
    self._pan = self._tilt = 0.0
    self.update(0.0, 0.0, 0.0)

  def off( self ):
    '''  '''
    self._pca.off(self._panPin)
    self._pca.off(self._tiltPin)

  #--------------------------------------------------------
  @property
  def rate( self ):
    return self._rate

  #--------------------------------------------------------
  @rate.setter
  def rate( self, aValue ):
    self._rate = aValue

  #--------------------------------------------------------
  def update( self, aPan, aTilt, aDT ):
    '''  '''
    self._pan = min(1.0, max(-1.0, self._pan + (aPan * aDT * self._rate)))
    self._tilt = min(1.0, max(-1.0, self._tilt + (aTilt * aDT * self._rate)))

    mn = camera._PANRANGE[1]
    perc = self._pan
    if perc < 0.0:
      mx = camera._PANRANGE[0]
      perc = -perc
    else:
      mx = camera._PANRANGE[2]

    r = mx - mn
    pan = (r * perc) + mn

    mn = camera._TILTRANGE[1]
    perc = self._tilt
    if perc < 0.0:
      mx = camera._TILTRANGE[0]
      perc = -perc
    else:
      mx = camera._TILTRANGE[2]

    r = mx - mn
    tilt = (r * perc) + mn

    self._pca.setangle(self._panPin, pan)
    self._pca.setangle(self._tiltPin, tilt)

