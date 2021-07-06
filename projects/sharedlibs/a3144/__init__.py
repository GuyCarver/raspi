#!/usr/bin/env python3

#driver for the a3144 hall effect sensor.

from ctypes import CDLL, POINTER, c_void_p, c_uint

_lib = CDLL(__path__[0] + '/a3144lib.so')
_lib.Create.restype = c_void_p
_lib.GetData.restype = POINTER(c_uint * 2)

#--------------------------------------------------------
def create( aPin ):
  return _lib.Create(aPin)

#--------------------------------------------------------
def release( aHall ):
  _lib.Release(aHall)

#--------------------------------------------------------
def data( aHall ):
  '''Get count, time.'''
  return _lib.GetData(aHall).contents



