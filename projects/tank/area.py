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
# FILE    area.py
# BY      gcarver
# DATE    04/12/2021 08:35 PM
#----------------------------------------------------------------------

from oled import oled
from oled.terminalfont import terminalfont

#--------------------------------------------------------
class area(object):
  '''System to display left/right/front obstructions on OLED display.'''

  _LPOS = (0, 32)
  _RPOS = (0, 40)
  _FPOS = (0, 48)

  #--------------------------------------------------------
  def __init__( self, aSideMax, aFrontMax ):
    ''' aSideMax is in us, aFrontMax is in mm. '''
    super(area, self).__init__()
    self._front = 0.0
    self._left = 0.0
    self._right = 0.0
    self._max = (aSideMax, aFrontMax)

    self._oled = oled()
    w, h = self._oled.size
    self._center = (w // 2, h // 2)

  #--------------------------------------------------------
  def update( self, aLeft, aRight, aFront ):
    ''' Draw left/right/front lines '''

    self._oled.clear()

    #Calculate line for left/right/front.

    lx = 0
    rx = self._oled.size[0] - 1
    fy = 0
    by = (self._oled.size[1] // 2) - 1

    bleft = aLeft < self._max[0]
    bright = aRight < self._max[0]
    bfront = aFront < self._max[1]

    if bleft:
      frac = aLeft / self._max[0]
      lx = self._center[0]  - int(self._center[0] * frac)

    if bright:
      frac = aRight / self._max[0]
      rx = self._center[0] + int(self._center[0] * frac)

    if bfront:
      frac = aFront / self._max[1]
      fy = self._center[1]  - int(self._center[1] * frac)
      self._oled.line((lx, fy), (rx, fy), True)

    if bright:
      self._oled.line((rx, fy), (rx, by), True)
    if bleft:
      self._oled.line((lx, fy), (lx, by), True)

    #Print distances.
    self._oled.text(area._LPOS, f'L: {aLeft}', 1, terminalfont)
    self._oled.text(area._RPOS, f'R: {aRight}', 1, terminalfont)
    self._oled.text(area._FPOS, f'F: {aFront}', 1, terminalfont)

    self._oled.display()
