
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
