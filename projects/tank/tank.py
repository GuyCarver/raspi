#!/usr/bin/env python3
# 08/22/2020 10:50 AM

# sudo apt install rpi.gpio

from pca9865 import *
from gamepad import *
from wheel import *
from buttons import gpioinit, button

import ps2con
import onestick
import RPi.GPIO as GPIO
# GPIO.setwarnings(False)
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(sentrybot._SMOKEPIN, GPIO.OUT)
# GPIO.output(sentrybot._SMOKEPIN, GPIO.HIGH if abTF else GPIO.LOW)
# GPIO.setup(channel, GPIO.IN, pull_up_down = GPIO.PUD_UP)
# res = GPIO.input(self._channel)

from time import perf_counter, sleep
import keyboard

gpioinit() # Initialize the GPIO system so we may use the pins for I/O.

_dtime = .03
_startupswitch = button(16)

#--------------------------------------------------------
def deadzone( aValue, aLimit ):
  return aValue if abs(aValue) >= aLimit else 0.0

#--------------------------------------------------------
class tank(object):

  # map of ps2 controller buttons to 8Bitdo FC30 Pro retro controller buttons.
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

  _HEADLIGHTS = (0, 1)
  _TAILLIGHTS = (2, 3)
  _DZ = 0.01                                    # Dead zone.

  #PS2 joystick is RX, RY, LX, LY while gamepad is LX, LY, RX, RY.
  _ps2joymap = (ps2con.LX, ps2con.LY, ps2con.RX, ps2con.RY)
  _speedchange = 0.25

#--------------------------------------------------------
  def __init__( self ):
    self._controllernum = 1                     #Type of controller 0=FC30, 1=ps2
    self._controller = None                     #Start out with no controller. Will set once we no which type.
    self._pca = pca9865(100)
    self._gpmacaddress = '' #'E4:17:D8:2C:08:68'
    self._buttonpressed = set()                 #A set used to hold button pressed states, used for debounce detection.
    self._left = wheel(self._pca, 8, 9, 10)
    self._right = wheel(self._pca, 4, 6, 5)
    self._lights = 0.0
    self.togglelights()

    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

    self._running = True

#--------------------------------------------------------
  def __del__( self ):
    self._contoller = None

#--------------------------------------------------------
  @property
  def macaddress( self ):
    return self._gpmacaddress

  @macaddress.setter
  def macaddress( self, aValue ):
    self._gpmacaddress = aValue
    if self.controllernum == 0 and self._controller != None:
      self._controller.macaddress = aValue

#--------------------------------------------------------
  @property
  def running( self ): return self._running

#--------------------------------------------------------
  @property
  def controllernum( self ): return self._controllernum

  @controllernum.setter
#--------------------------------------------------------
  def controllernum( self, aValue ):
    '''Set the controller #.'''
    self._controllernum = aValue
#    print('Controller:', self._controllernum)

#--------------------------------------------------------
  def _initcontroller( self ):
    '''Create the controller if necessary.'''
    if self._controllernum:
#      print('starting ps2 controller')
      self._controller = ps2con.ps2con(17, 27, 18, 4, self._ps2action)
    else:
#      print('starting Retro Controller')
      self._controller = gamepad(self.macaddress, self._buttonaction)

#--------------------------------------------------------
  def setcontroller( self, aIndex ):
    '''Set controller index if it changed, and create a controller.'''
    if self.controllernum != aIndex or self._controller == None:
      self.controllernum = aIndex
      self._initcontroller()

#--------------------------------------------------------
  def trypair( self ):
    '''If 8Bitdo controller is selected and it's not connected, attempt a pairing.'''
    if self.controllernum == 0 and self._controller != None and self._controller.connected == False:
      self._controller.pair()

#--------------------------------------------------------
  def _ps2action( self, aButton, aValue ):
    '''Callback for ps2 button events. They are remapped to FC30 events and sent
       to the _buttonaction callback.'''
    #Value of 2 indicates a change in pressed/released state.
    if aValue & 0x02:
      k = tank._ps2map[aButton]
      self._buttonaction(k, aValue)

#--------------------------------------------------------
  def _buttonaction( self, aButton, aValue ):
    '''Callback function for 8Bitdo FC30 Pro controller.'''

    #If button pressed
    if aValue & 0x01:
      self._buttonpressed.add(aButton)
      if aButton == ecodes.BTN_Y:
        self.brake()
      elif aButton == ecodes.BTN_TL:
        self._prevspeed()
      elif aButton == ecodes.BTN_TR:
        self._nextspeed()
    elif aButton == gamepad.GAMEPAD_DISCONNECT:
      self.brake()
    else: #Handle release events.
      if aButton == ecodes.BTN_X:
        self.togglelights()

      #On release, make sure to remove button from pressed state set.
      if aButton in self._buttonpressed:
        self._buttonpressed.remove(aButton)

#--------------------------------------------------------
  def setlights( self ):
    ''' Set all lights to self._lights value. '''
    if self._lights:
      for v in tank._HEADLIGHTS:
        self._pca.set(v, self._lights)
      for v in tank._TAILLIGHTS:
        self._pca.set(v, self._lights)
    else:
      for v in tank._HEADLIGHTS:
        self._pca.off(v)
      for v in tank._TAILLIGHTS:
        self._pca.off(v)

#--------------------------------------------------------
  def togglelights( self ):
    ''' Toggle lights on/off. '''
    # Max of 0.9 because 1.0 causes flickering, probably because we go slightly over max.
    self._lights = 0.9 -  self._lights
    self.setlights()

#--------------------------------------------------------
  def brake( self ):
    ''' Brake the wheels. '''
    self._left.brake()
    self._right.brake()
    #Sleep for a bit.
    sleep(0.2)
    self._left.off()
    self._right.off()

#--------------------------------------------------------
  def _nextspeed( self ):
    ''' Increment speed value. '''
    wheel.changegear(tank._speedchange)

#--------------------------------------------------------
  def _prevspeed( self ):
    ''' Decrement speed value. '''
    wheel.changegear(-tank._speedchange)

#--------------------------------------------------------
  def _joy( self, aIndex ):
    ''' Get joystick value in range -1.0 to 1.0 '''

    # PS2 controller has different stick mappings.
    if self._controllernum == 1:
      aIndex = tank._ps2joymap[aIndex & 0x03]  #Make sure value is in range.

    return self._controller.getjoy(aIndex) / 255.0

#--------------------------------------------------------
  def updatetracks( self ):
    ''' Update the track speeds. '''
    l = self._joy(gamepad._LY)
    r = self._joy(gamepad._RY)

    self._left.speed(deadzone(l, tank._DZ))
    self._right.speed(deadzone(r, tank._DZ))

#--------------------------------------------------------
  def run( self ):
    self._initcontroller()
    prevtime = perf_counter()

    while self.running:
      if self._haskeyboard and keyboard.is_pressed('q'):
        self._running = False
        print("quitting.")
      else:
        nexttime = perf_counter()
        delta = max(0.01, nexttime - prevtime)
        prevtime = nexttime
        if delta > _dtime:
          delta = _dtime

        if self._controller:
          self._controller.update()
          self.updatetracks()

        nexttime = perf_counter()
        sleeptime = _dtime - (nexttime - prevtime)  #30fps - time we've already wasted.
        if sleeptime > 0.0:
          sleep(sleeptime)

#--------------------------------------------------------
if __name__ == '__main__':
  #If the startup button is on then start up.
  _startupswitch.update()
  if len(sys.argv) > 1 or (_startupswitch.on):
    t = tank()
    t.run()
    GPIO.cleanup()
