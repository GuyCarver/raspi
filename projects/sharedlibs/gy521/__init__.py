#!/usr/bin/env python3
from ctypes import CDLL, POINTER, c_float, c_bool

_lib = CDLL(__path__[0] + '/gy521lib.so')
_lib.GetAccelTempRot.restype = POINTER(c_float * 7)
_lib.GetAcceleration.restype = POINTER(c_float * 3)
_lib.GetRotation.restype = POINTER(c_float * 3)
_lib.GetRPY.restype = POINTER(c_float * 3)

#--------------------------------------------------------
def startup(  ):
  b = c_bool(_lib.Startup())
  return b.value

#--------------------------------------------------------
def isgood(  ):
  b = c_bool(_lib.IsGood())
  return b.value

#--------------------------------------------------------
def shutdown(  ):
  _lib.Shutdown()

#--------------------------------------------------------
def getacceltemprot(  ):
  return _lib.GetAccelTempRot().contents

#--------------------------------------------------------
def getacceleration(  ):
  return _lib.GetAcceleration().contents

#--------------------------------------------------------
def getrotation(  ):
  '''Get array of rotations in range +/- pi.'''
  return _lib.GetRotation().contents

#--------------------------------------------------------
def getrpy( aDelta ):
  return _lib.GetRPY(c_float(aDelta)).contents

