#!/usr/bin/env python3

from pca9865 import *
from gamepad import *
from buttons import gpioinit, button
from kivy.clock import Clock
from kivy.base import EventLoop

import ps2con
import RPi.GPIO as GPIO
from wheels import wheel

from time import perf_counter, sleep
import keyboard

gpioinit() #Initialize the GPIO system so we may use the pins for I/O.

def gpioinit(  ):
  GPIO.setwarnings(False)
  GPIO.setmode(GPIO.BOARD)

def deadzone( aValue, aLimit ):
  return aValue if abs(aValue) >= aLimit else 0.0

_dtime = .03

class tank(object):

   #map of ps2 controller buttons to 8Bitdo FC30 Pro retro controller buttons.
  _ps2map = {
    ps2con.CIRCLE : ecodes.BTN_A,
    ps2con.CROSS : ecodes.BTN_B,
    ps2con.TRIANGLE : ecodes.BTN_X,
    ps2con.SQUARE : ecodes.BTN_Y,
    ps2con.SELECT : ecodes.BTN_SELECT,
    ps2con.START : ecodes.BTN_START,
    ps2con.L_TRIGGER : ecodes.BTN_TL2,
    ps2con.R_TRIGGER : ecodes.BTN_TR2,
    ps2con.L_SHOULDER : ecodes.BTN_TL,
    ps2con.R_SHOULDER : ecodes.BTN_TR,
    ps2con.L_HAT : ecodes.BTN_THUMBL,
    ps2con.R_HAT : ecodes.BTN_THUMBR,
    ps2con.DPAD_U : gamepad.BTN_DPADU,
    ps2con.DPAD_R : gamepad.BTN_DPADR,
    ps2con.DPAD_D : gamepad.BTN_DPADD,
    ps2con.DPAD_L : gamepad.BTN_DPADL
  }

  #PS2 joystick is RX, RY, LX, LY while gamepad is LX, LY, RX, RY.
  _ps2joymap = (ps2con.LX, ps2con.LY, ps2con.RX, ps2con.RY)

  _FC30, _PS2 = range(2)
  _LW, _RW = range(2)  #Left and right wheels.
  _WHEELPINS = ((0, 7, 11, 1), (1, 13, 15, 1))

  def __init__( self ):
    ''' '''
    self._pca = pca9865(100)
    self._controllernum = tank._FC30            #Type of controller _FC30 or _PS2
    self._controller = None                     #Start out with no controller. Will set once we no which type.
    self._gpmacaddress = '' #'E4:17:D8:2C:08:68'

    self._wheels = (wheel(self._pca, *d) for d ub tank._WHEELPINS)

    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

    self._running = True

  def __del__( self ):
    self._contoller = None

@property
  def macaddress( self ):
    return self._gpmacaddress

  @macaddress.setter
  def macaddress( self, aValue ):
    self._gpmacaddress = aValue
    #If the FC30 controller then set the mac address.
    if self.controllernum == tank._FC30 and self._controller != None:
      self._controller.macaddress = aValue

  @property
  def controllernum( self ):
    return self._controllernum

  @controllernum.setter
  def controllernum( self, aValue ):
    '''Set the controller #.'''
    self._controllernum = aValue
#    print('Controller:', self._controllernum)

  def _initcontroller( self ):
    '''Create the controller if necessary.'''
    if self._controllernum == tank._PS2:
#      print('starting ps2 controller')
      self._controller = ps2con.ps2con(18, 23, 24, 25, self._ps2action)
    else:
#      print('starting Retro Controller')
      self._controller = gamepad(self.macaddress, self._buttonaction)

  def setcontroller( self, aIndex ):
    '''Set controller index if it changed, and create a controller.'''
    if self.controllernum != aIndex or self._controller == None:
      self.controllernum = aIndex
      self._initcontroller()

   def _joy( self, aIndex ):
    '''Get joystick value in range -100.0 to 100.0'''

    #PS2 controller has different stick mappings.
    if self._controllernum == tank._PS2:
      aIndex = tank._ps2joymap[aIndex & 0x03]  #Make sure value is in range.

    return self._controller.getjoy(aIndex) / 2.55

  def _ps2action( self, aButton, aValue ):
    '''Callback for ps2 button events. They are remapped to FC30 events and sent
       to the _buttonaction callback.'''
#    print('Action:', aButton, aValue)
    #Value of 2 indicates a change in pressed/released state.
    if aValue & 0x02:
      k = tank._ps2map[aButton]
#     print(aButton, aValue, k)
      self._buttonaction(k, aValue)

  def _buttonaction( self, aButton, aValue ):
    '''Callback function for 8Bitdo FC30 Pro controller.'''

    print('Button:', gamepad.btntoname(aButton), aValue)

    if aValue & 0x01:
      pass
    elif aButton == gamepad.GAMEPAD_DISCONNECT:
      #Turn off wheels.
      for w in self._wheels:
        w.off()

      print('Disconnected controller!')

  def run( self ):
    '''  '''
    self._initcontroller()

    while self.running:
      if self._haskeyboard and keyboard.is_pressed('q'):
        self._running = False
        print("quitting.")
      else:
        nexttime = perf_counter()
        delta = max(0.01, nexttime - prevtime)
        prevtime = nexttime
        if delta > _dtime:
#          print("Clamping delta: ", delta)
          delta = _dtime

        #if controller exists and it updated successfully.
        if self._controller and self._controller.update():

#          rx = self._joy(gamepad._RX)
          ry = self._joy(gamepad._RY)
#          rx = deadzone(rx, 1.0)
          ry = deadzone(ry, 1.0)

#          lx = self._joy(gamepad._LX)
          ly = self._joy(gamepad._LY)

#          lx = deadzone(lx, 1.0)
          ly = deadzone(ly, 1.0)

          self._wheels[tank._RW].speed = ry
          self._wheels[tank._LW].speed = ly

        EventLoop.idle()                      #Update kivy event listener

        #Get how much time has passed since beginning of frame and subtract
        # that from the sleep time.
        nexttime = perf_counter()
        sleeptime = _dtime - (nexttime - prevtime)  #30fps - time we've already wasted.
        if sleeptime > 0.0:
          sleep(sleeptime)

if __name__ == '__main__':
  t = tank()
  t.run()