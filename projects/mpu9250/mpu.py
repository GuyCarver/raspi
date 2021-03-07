#!/usr/bin/env python3

#interface to the mpu9250.so module.

from ctypes import CDLL, POINTER, c_float

_lib = CDLL('./mpu9250.so')
_lib.GetAccelTempRot.restype = POINTER(c_float * 7)
_lib.GetMag.restype = POINTER(c_float * 3)

def startup(  ):
  _lib.Startup()

def shutdown(  ):
  _lib.Shutdown()

def suspend( bTF ):
  _lib.Suspend(bTF)

def getacceltemprot(  ):
  return _lib.GetAccelTempRot().contents

def getmag(  ):
  return _lib.GetMag().contents

def setmagangle( aAngle ):
  _lib.SetMagAngle(aAngle)


