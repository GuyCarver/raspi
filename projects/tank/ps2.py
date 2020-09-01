#!/usr/bin/env python3

from ctypes import CDLL, c_char_p, c_bool

_lib = CDLL("ps2con.so")

SELECT, L_HAT, R_HAT, START, DPAD_U, DPAD_R, DPAD_D, DPAD_L, L_TRIGGER, R_TRIGGER,
 L_SHOULDER, R_SHOULDER, TRIANGLE, CIRCLE,= CROSS, SQUARE, RX, RY, LX, LY = range(20)

def Startup( aCmd, aData, aClk, aAtt ):
  b = c_bool(_lib.Startup(aCmd, aData, aClk, aAtt))
  return b.value

def Shutdown(  ):
  _lib.Shutdown()

def Config(  ):
  _lib.Config()

def Update(  ):
  _lib.Update()

def GetButton( aIndex ):
  return _lib.GetButton(aIndex)

def GetJoy( aIndex ):
  return _lib.GetJoy(aIndex)

def GetName( aIndex ):
  b = c_char_p(_lib.GetName(aIndex))
  return b.value

def GetString(  ):
  b = c_char_p(_lib.GetString())
  return b.value
