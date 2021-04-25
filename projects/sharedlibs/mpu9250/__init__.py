#!/usr/bin/env python3

#interface to the mpu9250.so module.

from ctypes import CDLL, POINTER, c_float

_lib = CDLL(__path__[0] + '/mpu9250lib.so')
_lib.GetRotTempAccel.restype = POINTER(c_float * 7)
_lib.GetMag.restype = POINTER(c_float * 3)

def startup(  ):
  _lib.Startup()

def shutdown(  ):
  _lib.Shutdown()

def suspend( bTF ):
  _lib.Suspend(bTF)

def getrottempaccel(  ):
  return _lib.GetRotTempAccel().contents

def getmag(  ):
  return _lib.GetMag().contents

def setmagangle( aAngle ):
  _lib.SetMagAngle(aAngle)


