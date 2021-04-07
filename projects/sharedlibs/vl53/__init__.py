#!/usr/bin/env python3

from ctypes import CDLL, c_bool, c_float

# Located in usr/local/bin
_lib = CDLL(__path__[0] + '/vl53lib.so')
_lib.Create.restype = c_void_p

def create( aAddress, aType ):
  return _lib.Create(aAddress, aType)

def release( aInstance ):
  _lib.Release(aInstance)

def setaddress( aInstance, aAddress ):
  _lib.SetAddress(aInstance, aAddress)

def getdata( aInstance ):
  _lib.GetData(aInstance)
