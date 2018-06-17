
from math import radians, sin, cos

def rotate( aPos, aCosSin ) :
  '''Rotate (x, y) position by (cos, sin) and return new (x, y)'''
  x, y = aPos
  c, s = aCosSin

  nx = x * c - y * s
  ny = x * s + y * c

  return (nx, ny)

def cossin( aAngle ) :
  '''Return (cos, sin) of given angle in degrees'''
  aAngle = radians(aAngle)
  return (cos(aAngle), sin(aAngle))

def calcbounds( aAngle, xs, ys ):
  '''Calculate the virtual bounds given an angle and servo x,y min/max ranges.'''
  cs, sn = cossin(aAngle)
  x0 = xs[0] * cs
  x1 = xs[1] * cs
  y0 = ys[0] * (1.0 - sn)
  y1 = ys[1] * (1.0 - sn)
#  print(y0, y1)

  return (x0, x1), (y0, y1)
