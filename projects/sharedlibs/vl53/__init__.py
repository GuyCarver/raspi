#!/usr/bin/env python3
#Driver for VL530X laser range finder.

from ctypes import CDLL, c_void_p, c_ushort

# Located in usr/local/bin
_lib = CDLL(__path__[0] + '/vl53lib.so')
_lib.Create.restype = c_void_p
_lib.Distance.restype = c_ushort

#--------------------------------------------------------
def create( aAddress = 0, bLongDistance = False ):
  '''Address of 0 with force the system to use the default address.
      Long Distance true seems to actually shorten the distance.'''
  return _lib.Create(aAddress, bLongDistance)

#--------------------------------------------------------
def release( aInstance ):
  _lib.Release(aInstance)

#--------------------------------------------------------
def update( aInstance ):
  ''' Call this to trigger a distance read, wait at least 40ms
       before calling distance to ensure you get the latest value. '''
  _lib.Update(aInstance)

#--------------------------------------------------------
def distance( aInstance ):
  ''' Get the last read distance. Call update to get a new value.
       Wait at least 40ms after an update call before reading to
       ensure you get a new value. '''
  return _lib.Distance(aInstance)
