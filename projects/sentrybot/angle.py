
from math import sin, cos

def rotate( aPos, aSinCos ) :
    x, y = aPos
    c, s = aSinCos

    nx = x * c - y * s
    ny = x * s + y * c

    return (nx, ny)

def cossin( aAngle ) :
  return (cos(aAngle), sin(aAngle))
