#!/usr/bin/env python3

#driver for the HC-SR04 sonic distance sensor.

from ctypes import CDLL, POINTER, c_void_p, c_uint

_lib = CDLL(__path__[0] + '/hcsr04lib.so')
_lib.Create.restype = c_void_p

#--------------------------------------------------------
def create( aTrigger, aEcho ):
  return _lib.Create(aTrigger, aEcho)

#--------------------------------------------------------
def release( aInstance ):
  _lib.Release(aInstance)

#--------------------------------------------------------
def update( aInstance ):
  '''Get delay in microseconds from echo.'''
  return _lib.Update(aInstance)



