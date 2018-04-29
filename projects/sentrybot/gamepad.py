#!/usr/bin/env python3
#8Bitdo FC30 Pro device driver
#

from evdev import InputDevice, ecodes, list_devices
import os
from time import sleep

debug = 0

#evdev Button codes are as follows, type = 1 and val is 0 or 1 for buttons.
#types EV_KEY = 1, vals will be 0 or 1.
#BTN_A = 304
#BTN_B = 305
#BTN_C = 306 Power button
#BTN_X = 307
#BTN_Y = 308
#BTN_SELECT = 314
#BTN_START = 315
#BTN_TL2 = 312
#BTN_TR2 = 313
#BTN_TL = 310 lshoulder
#BTN_TR = 311 rshoulder
#BTN_THUMBL = 317 lhat
#BTN_THUMBR = 318 rhat

#type EV_ABS = 3
#ABS_X = 0, val = 0-255 255=right lthumb left/right
#ABS_Y = 1, val = 0-255 255=forward lthumb up/down
#ABS_Z = 2, val = 0-255 rthumb left/right
#ABS_RZ = 5, val = 0-255 rthumb up/down
#ABS_HAT0X = 16, val = -1 or 1 dpad left/right
#ABS_HAT0Y = 17, val = -1 or 1 dpad up/down

class gamepad(object):
  '''8Bitdo FC30 Pro gamepad device driver.'''

  _NAME = '8Bitdo FC30 Pro'

  _LX = 0 #ecodes.ABS_X
  _LY = 1 #ecodes.ABS_Y
  _RX = 2 #ecodes.ABS_Z
  _RY = 3 #This one isn't mapped right so we convert ABS_RZ(5) to 3.

  @staticmethod
  def _translate( aValue, aInvert ):
    '''Convert value 0-255 to +/-256
       aInvert indicates we should negate'''
    sgn = -1 if aInvert else 1
    return ((aValue - 0x80) << 1) * sgn

  @staticmethod
  def finddevice(  ):
    '''Find the correct device by name.'''
    devices = [InputDevice(fn) for fn in list_devices()]
    for d in devices:
      if d.name == gamepad._NAME:
        return d
    return None

  def __init__( self, aID = 'E4:17:D8:2C:08:68', aCallback = None ):
    '''aID is the bluetooth device ID reported by bluetoothctl during pairing.
       aCallback is the callback function to call for processing button events.'''
    self._id = aID
    self._joys = [0] * 4
    self._callback = None
    self._device = None
    self._input = ''
    self._connect()
    self.update()
    self._callback = aCallback

  def __del__( self ):
    self.shutdown()

  def shutdown( self ):
    '''Disconnect from the gamepad'''
    self._disconnect()
    try:
      os.system('echo "disconnect ' + self._id + ' \nquit" | sudo bluetoothctl')
    except:
      pass

  @property
  def callback( self ):
    return self._callback

  @callback.setter
  def callback( self, aCallback ):
    self._callback = aCallback

  @property
  def connected( self ):
    return self._device != None

  def _disconnect( self ):
    '''Soft disconnect, kill the InputDevice'''
    self._device = None

  def _connect( self, aTries = 20 ):
    '''Attempt to connect to the gamepad and create the InputDevice'''
    self._disconnect()

    for i in range(aTries):
      if debug:
        print("connect attempt {} for {}".format(i, self._id))
      try:
        os.system('echo "power on \nconnect ' + self._id + ' \nquit" | sudo bluetoothctl')

        for j in range(5):
          sleep(1.0)
          self._device = gamepad.finddevice()
          sleep(0.1)
          print('connected!')
          return self.connected
      except Exception as e:
        if debug:
          if debug > 1:
            raise(e)
          print(e)

      sleep(1.0)

    return self.connected

  def _docallback( self, aEvent ):
    '''If callback exists, call it with the given values.'''
    if self._callback:
      self._callback(aEvent.code, aEvent.value)

  def joy( self, aIndex ):
    '''Get joystick value for given index _LX, _LY, _RX or _RY'''
    return self._joys[aIndex]

  def update( self ):
    '''Read events fromt he input device, update joy values
       and use callback to process button events.'''
    if self.connected:
      try:
        for event in self._device.read():
          if event.type == ecodes.EV_KEY:
#            print(event)
            self._docallback(event)
          elif event.type == ecodes.EV_ABS:
            if ecodes.ABS_HAT0X <= event.code <= ecodes.ABS_HAT0Y:
#              print(event)
              self._docallback(event)
            elif event.code <= 5: #l/r triggers pass abs codes in as well as btn codes.
#              print(event)
              #This code is 5 but we want 0-3
              if event.code == ecodes.ABS_RZ:
                event.code = gamepad._RY
              self._joys[event.code] = gamepad._translate(event.value, event.code & 1)
      except Exception as e:
        if debug:
          if debug > 1:
            raise e
          print(e)
    else:
      self._connect(1)

def mytest( aButton, aValue ):
  '''Test input.'''
  def printbtn(btn, v):
    print(btn + (' pressed' if v else ' released'))

  btn = ''
  if aButton == ecodes.BTN_A:
    btn = 'A'
  elif aButton == ecodes.BTN_B:
    btn = 'B'
  elif aButton == ecodes.BTN_C:
    btn = 'C'
  elif aButton == ecodes.BTN_X:
    btn = 'X'
  elif aButton == ecodes.BTN_Y:
    btn = 'Y'
  elif aButton == ecodes.BTN_START:
    btn = 'START'
  elif aButton == ecodes.BTN_SELECT:
    btn = 'SELECT'
  elif aButton == ecodes.BTN_TR2:
    btn = 'rtrigger'
  elif aButton == ecodes.BTN_TL2:
    btn = 'ltrigger'
  elif aButton == ecodes.BTN_TR:
    btn = 'rshoulder'
  elif aButton == ecodes.BTN_TL:
    btn = 'lshoulder'
  elif aButton == ecodes.BTN_THUMBL:
    btn = 'lhat'
  elif aButton == ecodes.BTN_THUMBR:
    btn = 'rhat'
  elif aButton == ecodes.ABS_HAT0X:
    btn = 'dpadr' if aValue > 0 else 'dpadl'
  elif aButton == ecodes.ABS_HAT0Y:
    btn = 'dpadu' if aValue > 0 else 'dpadd'

  printbtn(btn, aValue)

if __name__ == '__main__':  #start server
  p = gamepad(aCallback = mytest)
  while 1:
    p.update()
    sleep(0.1)
