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
# FILE    onestick.py
# BY      gcarver
# DATE    04/04/2021 11:11 AM
#----------------------------------------------------------------------

points = [(1.0,1.0), (1.0,0.0), (1.0,-1.0), (-1.0,0.0), (-1.0,-1.0), (0.0,-1.0), (-1.0,1.0), (0.0,1.0)]
triangles = ((4,5,6), (4,3,2), (0,7,6), (0,1,2))

#Quadrants, triangle indexes for quadrants, points.
#|-------|          7--0--1          (0,1)---(1,1)---(1,0)
#| 2 | 3 |          |  |  |            |       |       |
#|---|---|          6--+--2         (-1,1)---(0,0)---(1,-1)
#| 0 | 1 |          |  |  |            |       |       |
#|-------|          5--4--3         (0,-1)--(-1,-1)--(-1,0)

#To get L/R speeds from x,y input -1 to 1.
#Determine quadrant for point.
#Determine point to use based on if y > x.
#  Point 1 and origin are constant.
#  If y > x point 0, otherwise point 2.

def interp( t1, t2, v ):
  '''Interpolate between t1 and t2 by v.'''
  x1, y1 = t1
  x1 += ((t2[0] - x1) * v)
  y1 += ((t2[1] - y1) * v)
  return (x1, y1)

def adjustpoints( aValue ):
  '''Replaces all 0s in the points list to the given value.'''
  global points
  points[1] = (points[1][0], aValue)
  points[3] = (points[3][0], -aValue)
  points[5] = (-aValue, points[5][1])
  points[7] = (aValue, points[7][1])

def vels( x, y ):
  '''p0--p1
    |   / |
    | /   |
    0,0  p2
   '''
  #Get quadrant 0-4 from point.
  q = ((y >= 0) << 1) | (x >= 0)

  #Get triangle points for the quadrant.
  t0, t1, t2 = triangles[q]

  #Once we have the quadrant we use the absolute value of x,y (range 0-1).
  x = abs(x)
  y = abs(y)

  #Get the middle point.
  p1 = points[t1]

  #Interp between (0,0) and triangle point 1 (diagonal).
  v1 = (p1[0] * x, p1[1] * y)

  #NOTE: If y==x we could simply return v1, however that probably
  # rarely happens so it's not worth the extra time to check.

  #y >= x so interp between triangle point 0 and 1 using x.
  if y >= x:
    p0 = points[t0]
    x, y = y, x                                 # Swap x, y for the perc calc.
  #x > y so interp between triangle point 2 and 1 using y.
  else:
    p0 = points[t2]

  v2 = interp(p0, p1, y)
  #Convert x to a value between 0 and 1 relative to y.
  perc = 1.0 if x >= 1.0 else (x - y) / (1.0 - y)

  #Interpolate between v1 and v2 by percentage.
  res = interp(v1, v2, perc)
  return res

# tests = ((0.5, 0.51), (1,.99), (0,.99), (1,0.1), (1,-.99), (0,-.99), (-1,-.99), (-1,0.1), (-1,.99))
# def test(  ):
#   for t in tests:
#     r = vels(*t)
#     print(r)
#
# test()

# (0.51, 0.010000000000000009)
# (1.0, -0.010000000000000009)
# (0.99, 0.99)
# (1.0, -0.9)
# (-0.98, -0.010000000000000009)
# (-0.99, -0.99)
# (-0.010000000000000009, -0.98)
# (-0.9, 1.0)
# (-0.010000000000000009, 1.0)

