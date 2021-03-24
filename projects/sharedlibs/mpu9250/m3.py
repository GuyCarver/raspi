#!/usr/bin/env python3

#interface to the m3.so module.

from ctypes import CDLL, POINTER, c_float, c_void_p, c_uint

_lib = CDLL('./m3lib.so')
_lib.Rotate.restype = POINTER(c_float * 3)
_lib.ZRotation.restype = POINTER(c_void_p)

#testvalue = c_uint.in_dll(_lib, "TestValue").value

def ZRotation( aAngle ):
  return _lib.ZRotation(c_float(aAngle))

def Release( aMatrix ):
  _lib.Release(aMatrix)

def Rotate( aMatrix, x, y, z ):
  return _lib.Rotate(aMatrix, c_float(x), c_float(y), c_float(z)).contents


