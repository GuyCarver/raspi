#!/usr/bin/env python3

from ctypes import CDLL, c_uint32, c_char_p, c_bool

_lib = CDLL(__path__[0] + '/ps2conlib.so')

SELECT, L_HAT, R_HAT, START, DPAD_U, DPAD_R, DPAD_D, DPAD_L, L_TRIGGER, R_TRIGGER, L_SHOULDER, R_SHOULDER, TRIANGLE, CIRCLE, CROSS, SQUARE, RX, RY, LX, LY = range(20)

def Startup( aCmd, aData, aClk, aAtt ):
  '''Startup singleton PS2 controller with Cmd, Data, Clk, Att pin numbers.'''
  b = c_bool(_lib.Startup(aCmd, aData, aClk, aAtt))
  return b.value

def Shutdown(  ):
  '''Shut down the singleton PS2 controller.'''
  _lib.Shutdown()

def Config(  ):
  _lib.Config()

def Events( aNumber, aCallback ):
  ''' Process button events with Callback( button, event ).'''
  for i in range(aNumber):
    b = _lib.GetEvent(i)
    if b & 0x2:
      btn = b >> 8
      evt = b & 0x3
      aCallback(btn, evt)

def Update( aCallback = None ):
  '''Update and process events if callback is given. See Events().'''
  es = _lib.Update()
  if aCallback:
    Events(es, aCallback)

def NumButtons(  ):
  return _lib.NumButtons()

def GetButton( aIndex ):
  return _lib.GetButton(aIndex)

def GetJoy( aIndex ):
  '''Get Joystick value +/-255.'''
  return _lib.GetJoy(aIndex)

def GetName( aIndex ):
  '''Get name of button.'''
  b = c_char_p(_lib.GetName(aIndex))
  return b.value

def GetString(  ):
  '''Get string showing all button values.'''
  b = c_char_p(_lib.GetString())
  return b.value
