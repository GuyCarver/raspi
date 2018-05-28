#!/usr/bin/env python3
#8Bitdo FC30 Pro device driver
#

from evdev import InputDevice, ecodes, list_devices
import os
import pyudev
from time import sleep

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

  debug = 0
  _NAME = '8Bitdo FC30 Pro'

  _LX = 0 #ecodes.ABS_X
  _LY = 1 #ecodes.ABS_Y
  _RX = 2 #ecodes.ABS_Z
  _RY = 3 #This one isn't mapped right so we convert ABS_RZ(5) to 3.

  BTN_DPADU = 4
  BTN_DPADR = 5
  BTN_DPADD = 6
  BTN_DPADL = 7

  GAMEPAD_DISCONNECT = 32                       #Special button action to indicate disconnect.

  _buttonnames = {
   'A' : ecodes.BTN_A,
   'B' : ecodes.BTN_B,
   'C' : ecodes.BTN_C,
   'X' : ecodes.BTN_X,
   'Y' : ecodes.BTN_Y,
   'SLCT' : ecodes.BTN_SELECT,
   'STRT' : ecodes.BTN_START,
   'L_TR' : ecodes.BTN_TL2,
   'R_TR' : ecodes.BTN_TR2,
   'L_SH' : ecodes.BTN_TL,
   'R_SH' : ecodes.BTN_TR,
   'L_TH' : ecodes.BTN_THUMBL,
   'R_TH' : ecodes.BTN_THUMBR,
   'DP_U' : BTN_DPADU,
   'DP_R' : BTN_DPADR,
   'DP_D' : BTN_DPADD,
   'DP_L' : BTN_DPADL
  }

  @classmethod
  def nametobtn( self, aValue ):
    '''Get button # of given button name'''
    return self._buttonnames[aValue] if aValue in self._buttonnames else -1

  @classmethod
  def btntoname( self, aButton ):
    '''Get the name given a button value.'''
    for k, v in self._buttonnames.items():
      if v == aButton:
        return k

    return None

  @staticmethod
  def _translate( aValue, aInvert ):
    '''Convert value 0-255 to +/-255
       aInvert indicates we should negate'''
    sgn = -1 if aInvert else 1
    return (((aValue - 0x80) << 1) + 1) * sgn

  @staticmethod
  def finddevice(  ):
    '''Find the correct device by name.'''
    devices = [InputDevice(fn) for fn in list_devices()]
    for d in devices:
      if d.name == gamepad._NAME:
        return d
    return None

  @staticmethod
  def isconnected(  ):
    '''  '''
    return gamepad.finddevice() != None

  def __init__( self, aID = 'E4:17:D8:2C:08:68', aCallback = None ):
    '''aID is the bluetooth device ID reported by bluetoothctl during pairing.
       aCallback is the callback function to call for processing button events.'''
    self.monitorconnections()
    self._dcondetect = False                    #Set to true when disconnect detected.
    self._errcount = 0
    self._id = aID
    self._joys = [0] * 4
    self._callback = None
    self._device = None
    self._input = ''
    self._connect()
    self.update()
    self._callback = aCallback

  def __del__( self ):
    self._observer.stop()
    self._disconnect()
    try:
      os.system('echo "disconnect ' + self._id + ' \nquit" | sudo bluetoothctl')
    except:
      pass

  def monitorconnections( self ):
    '''Monitor the udev system for device disconnect.'''
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)

    #Watch for js0 remove event and flag disconnect to be handled by main thread.
    # Don't know why it's called JS0, but that's what testing showed.
    def eventhandler( action, device ):
      if action == 'remove' and device.sys_name == 'js0':
        self._dcondetect = True

    self._observer = pyudev.MonitorObserver(monitor, eventhandler)
    self._observer.start()

  @property
  def callback( self ):
    return self._callback

  @callback.setter
  def callback( self, aCallback ):
    '''Set the callback.  Callback is func(button, value)
       value is 1 if pressed else released.  On disconnect
       button = gamepad.GAMEPAD_DISCONNECT and value = 0.'''
    self._callback = aCallback

  @property
  def connected( self ):
    return self._device != None

  def _disconnect( self ):
    '''Soft disconnect, kill the InputDevice'''
    self._device = None

    #If disconnect was detected, send special event to callback.
    if self._dcondetect and self._callback:
      self._callback(gamepad.GAMEPAD_DISCONNECT, 0)
      self._dcondetect = False

  def _connect( self, aTries = 20 ):
    '''Attempt to connect to the gamepad and create the InputDevice'''
    self._disconnect()

    for i in range(aTries):
      if gamepad.debug:
        print("connect attempt {} for {}".format(i, self._id))
      try:
        os.system('echo "power on \nconnect ' + self._id + ' \nquit" | sudo bluetoothctl')

        for j in range(5):
          sleep(1.0)
          self._device = gamepad.finddevice()
          if self.connected:
            sleep(0.1)
            print('connected!')
            return self.connected
      except Exception as e:
        if gamepad.debug:
          if gamepad.debug > 1:
            raise(e)
          print(e)

      sleep(1.0)

    return self.connected

  def _docallback( self, aEvent ):
    '''If callback exists, call it with the given values.'''
    if self._callback:
      self._callback(aEvent.code, aEvent.value)

  def getjoy( self, aIndex ):
    '''Get joystick value for given index _LX, _LY, _RX or _RY
       Value is range +/- 255.'''
    return self._joys[aIndex]

  def update( self ):
    '''Read events from the input device, update joy values
       and use callback to process button events.'''
    if self.connected and not self._dcondetect:
      try:
        for event in self._device.read():
          if event.type == ecodes.EV_KEY:
#            print(event)
            self._docallback(event)
          elif event.type == ecodes.EV_ABS:
            #turn hat x,y +/- values to dpad button events.
            if event.code == ecodes.ABS_HAT0X:
              event.code = gamepad.BTN_DPADR if event.value > 0 else gamepad.BTN_DPADL
              self._docallback(event)
            elif event.code == ecodes.ABS_HAT0Y:
              event.code = gamepad.BTN_DPADU if event.value > 0 else gamepad.BTN_DPADD
              self._docallback(event)
            elif event.code <= 5: #l/r triggers pass abs codes in as well as btn codes.
#              print(event)
              #This code is 5 but we want 0-3
              if event.code == ecodes.ABS_RZ:
                event.code = gamepad._RY
              self._joys[event.code] = gamepad._translate(event.value, event.code & 1)
        self._errcount = 0
      except Exception as e:
        #When not getting values we get resource unavailable messages.  Count them
        # and run reconnect if we get too many.
        self._errcount += 1
        if self._errcount > 2000:
          self._errcount = 1000
          self._connect(1)
        if gamepad.debug:
          if gamepad.debug > 1:
            raise e
          print(e)
    else:
      self._connect(1)

if __name__ == '__main__':  #start server

  def mytest( aButton, aValue ):
    '''Test input.'''
    if aButton == ecodes.ABS_HAT0X:
      btn = 'dpadr' if aValue > 0 else 'dpadl'
    if aButton == ecodes.ABS_HAT0Y:
      btn = 'dpadu' if aValue > 0 else 'dpadd'
    else:
      btn = gamepad.btntoname(aButton)

    print(btn, ('pressed' if aValue else 'released'))

  p = gamepad(aCallback = mytest)
  while 1:
    p.update()
    j1 = p.getjoy(p._RY)
    print("Joy: ", j1, "      ", end="\r")
    sleep(0.1)
