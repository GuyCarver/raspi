#!/usr/bin/env python3

#driver for the HC-SR04 sonic distance sensor.
#Call update to cause the sensor to read a value.
#Get that value with gettime(). It's best to separate these
# 2 calls by enough time to allow the read to occur. This could
# be as much as 38ms.

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
  ''' Update the value on the echo. '''
  _lib.Update(aInstance)

#--------------------------------------------------------
def gettime( aInstance ):
  ''' Read the time value from the echo. '''
  return _lib.Read(aInstance)


