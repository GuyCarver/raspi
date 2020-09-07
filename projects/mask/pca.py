#!/usr/bin/env python3

from ctypes import CDLL, c_bool, c_float

# Located in usr/local/bin
_lib = CDLL("pca9865.so")

def Startup(  ):
  b = c_bool(_lib.Startup())
  return b.value

def IsGood(  ):
  b = c_bool(_lib.IsGood())
  return b.value

def Shutdown(  ):
  _lib.Shutdown()

def SetFreg( aFreq ):
  _lib.SetFreq(aFreq)

def Off( aIndex ):
  _lib.Off(aIndex)

def AllOff(  ):
  _lib.AllOff()

def Set( aIndex, aValue ):
  _lib.Set(aIndex, c_float(aValue))

def SetAngle( aIndex, aAngle ):
  _lib.SetAngle(aIndex, c_float(aAngle))
