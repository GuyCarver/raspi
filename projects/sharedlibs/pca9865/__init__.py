#!/usr/bin/env python3

from ctypes import CDLL, c_bool, c_float

# Located in usr/local/bin
_lib = CDLL(__path__[0] + '/pca9865lib.so')

def startup(  ):
  b = c_bool(_lib.Startup())
  return b.value

def isgood(  ):
  b = c_bool(_lib.IsGood())
  return b.value

def shutdown(  ):
  _lib.Shutdown()

def setfreq( aFreq ):
  _lib.SetFreq(aFreq)

def setpwm( aIndex, aOn, aOff ):
  _lib.SetPWM(aIndex, aOn, aOff)

def off( aIndex ):
  _lib.Off(aIndex)

def alloff(  ):
  _lib.AllOff()

def set( aIndex, aValue ):
  _lib.Set(aIndex, c_float(aValue))

def setangle( aIndex, aAngle ):
  _lib.SetAngle(aIndex, c_float(aAngle))
