#!/usr/bin/env python3
# 08/22/2020 10:50 AM

# sudo apt install rpi.gpio

#todo: Figure out what is causes the input delay.
#todo: Add limits for camera movement.
#todo: Add animation of camera movement rather than direct controller input.
#todo: Test using x axis for camera control during movement.
#todo: Add light sensor so we know when it's dark
#todo: Add sound sensor to listen for triggers
#todo: Add motion sensor?
#todo: Put gamepad update into thread?

import sys
from gamepad import *
from wheel import *
from strobe import *
from sides import *
import state

import vl53
import pca9865 as pca
import onestick

from time import perf_counter, sleep
from buttons import gpioinit, button
import keyboard

_DISPLAY = True                                   # Set this to true to support oled output.
if _DISPLAY:
  from area import *

gpioinit() # Initialize the GPIO system so we may use the pins for I/O.

_dtime = .03
_startupswitch = button(16)

#--------------------------------------------------------
def deadzone( aValue, aLimit ):
  return aValue if abs(aValue) >= aLimit else 0.0

#--------------------------------------------------------
class tank(object):

  _MACADDRESS = '41:42:E4:57:3E:9E'             # Controller mac address

#--------------------------------------------------------
#__RASPI Pin Indexes
  _LSIDE = (9, 10)                              # Left/right distance sensor (trigger/echo) pins.
  _RSIDE = (17, 18)

  _SPEEDOL = 27                                 # Input pins for speedometer reading
  _SPEEDOR = 22

  _STROBERED = 23                               # Pins to control red/blue strobe lights
  _STROBEBLUE = 24

  _LIGHTBANK = 25                               # Pin to control bank of 12v lights on front of tank

#--------------------------------------------------------
#__PCA Indexes.
  _HEADLIGHTS = (0, 1)
  _TAILLIGHTS = (2, 3)
  _RS, _RF, _RB = 4, 6, 5
  _LS, _LF, _LB = 8, 9, 10                      # Left/Right speed, forward, backward pins

  _CAMERAPAN = 12                               # Front camera pca indexes for pan/tilt
  _CAMERATILT = 13

#--------------------------------------------------------
#__Misc values
  _DZ = 0.015                                   # Gamepad Dead zone.
  _SPEEDCHANGE = 0.25
  _MAXSIDE = 3200                               # In us.
  _MAXFRONT = 560                               # In mm.

  _CONNECT, _HUMAN, _CAMERACONTROL, _TURNING, _MOVEFWD = range(5)


#--------------------------------------------------------
  def __init__( self ):

    pca.startup()
    self._gpmacaddress = '' #'E4:17:D8:2C:08:68'
    self._buttonpressed = set()                 # A set used to hold button pressed states, used for debounce detection and button combos. #
    self._left = wheel(pca, tank._LS, tank._LF, tank._LB, tank._SPEEDOL)
    self._left.name = 'lw'
    self._right = wheel(pca, tank._RS, tank._RF, tank._RB, tank._SPEEDOR)
    self._right.name = 'rw'
    self._lights = 0.0
    self._onestick = False
    self._sides = sides(tank._LSIDE, tank._RSIDE)  # Left/Right Pin #s for trigger/echo.
    self._front = vl53.create()

    #Initialize the states.
    self._states = {}
    self._states[tank._CONNECT] = state.create(u = self._connectUD)
    self._states[tank._HUMAN] = state.create(u = self._humanUD, i = self._humanIN)
    self._states[tank._CAMERACONTROL] = state.create(u = self._cameraUD, i = self._cameraIN)
    self._states[tank._TURNING] = state.create()
    self._states[tank._MOVEFWD] = state.create(s = self._movefwdST, u = self._movefwdUD)
    self._curstate = tank._CONNECT

    self._strobe = strobe(tank._STROBERED, tank._STROBEBLUE)
    self._lightbank = lightbank(tank._LIGHTBANK)

    self.togglelights()
    onestick.adjustpoints(tank._DZ)             # Set point to minimum value during interpretation.

    self._controller = gamepad(tank._MACADDRESS, self._buttonaction)

    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

    if _DISPLAY:
      self._area = area(tank._MAXSIDE, tank._MAXFRONT)

    self._running = True

#--------------------------------------------------------
  def __del__( self ):
    pca.alloff()
    self._strobe.on = False
    self._lightbank.on = False

#--------------------------------------------------------
  @property
  def running( self ): return self._running

#--------------------------------------------------------
  def _buttonaction( self, aButton, aValue ):
    '''Callback function for controller.'''
    state.input(self.stateobj, aButton, aValue)

#--------------------------------------------------------
  def setlights( self ):
    ''' Set all lights to self._lights value. '''
    if self._lights:
      for v in tank._HEADLIGHTS:
        pca.set(v, self._lights)
      for v in tank._TAILLIGHTS:
        pca.set(v, self._lights)
    else:
      for v in tank._HEADLIGHTS:
        pca.off(v)
      for v in tank._TAILLIGHTS:
        pca.off(v)

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
    wheel.changegear(tank._SPEEDCHANGE)

#--------------------------------------------------------
  def _prevspeed( self ):
    ''' Decrement speed value. '''
    wheel.changegear(-tank._SPEEDCHANGE)

#--------------------------------------------------------
  def _joy( self, aIndex ):
    ''' Get joystick value in range -1.0 to 1.0 '''
    v = self._controller.getjoy(aIndex)
    return v / 255.0

#--------------------------------------------------------
  def _joydz( self, aInput ):
    ''' Get joystick value and remove deadzone. '''

    v = self._joy(aInput)
    return v if abs(v) >= tank._DZ else 0.0

#--------------------------------------------------------
  @property
  def stateobj( self ):
    return self._states[self._curstate]

#--------------------------------------------------------
  @property
  def curstate( self ):
    return self._curstate

#--------------------------------------------------------
  @curstate.setter
  def curstate( self, aState ):
    ''' Set and start a new state if changed and end the previous one. '''
    if self._curstate != aState:
      state.end(self.stateobj)
      self._curstate = aState
      state.start(self.stateobj)

#--------------------------------------------------------
  def _connectUD( self, aState, aDT ):
    ''' State for controller connect. '''
    self._controller.update()
    if self._controller.isconnected():
      self.curstate = tank._HUMAN

#--------------------------------------------------------
  def _sharedUD( self, aDelta ):
    ''' Updates to system shared by most states. '''
    vl53.update(self._front)                    # Update front distance
    self._sides.update()                        # Update the side distance sensors
    self._strobe.update(aDelta)
    self._controller.update()

    if _DISPLAY:
      # Disply front/side distances.
      l, r = self._sides.gettimes()
      f = vl53.distance(self._front)
      self._area.update(l, r, f)

#--------------------------------------------------------
  def _humanUD( self, aState, aDT ):
    ''' Update method for human control state. '''

    self._sharedUD(aDT)

    l = self._joydz(gamepad._LY)
    if self._onestick:
      r = -self._joydz(gamepad._LX)
      r, l = onestick.vels(r, l)
    else:
      r = -self._joydz(gamepad._RY)

    self._left.speed(l)
    self._left.update(aDT)
    self._right.speed(r)
    self._right.update(aDT)
#     print('        ', end='\r')

#--------------------------------------------------------
  def _humanIN( self, aState, aButton, aValue ):
    '''  '''
    #Capture exceptions so we can print them because the gamepad driver catches and ignores
    # exceptions to control behaviour for controller issues.
    try:
      #If button pressed
      if aValue & 0x01:
        self._buttonpressed.add(aButton)
        if aButton == ecodes.BTN_B:
          self.brake()
        elif aButton == ecodes.BTN_TL:
          self._prevspeed()
        elif aButton == ecodes.BTN_TR:
          self._nextspeed()
        elif aButton == ecodes.BTN_SELECT:
          self._onestick = not self._onestick
        elif aButton == ecodes.BTN_A:
          self._lightbank.toggle()
        elif aButton == ecodes.BTN_X:
          self._strobe.toggle()
        elif aButton == ecodes.BTN_THUMBR:
          self.curstate = tank._CAMERACONTROL
        elif aButton == gamepad.BTN_DPADU:
          self.curstate = tank._MOVEFWD
      elif aButton == gamepad.GAMEPAD_DISCONNECT:
        self.brake()
      else: #Handle release events.
        if aButton == ecodes.BTN_Y:
          self.togglelights()

        #On release, make sure to remove button from pressed state set.
        if aButton in self._buttonpressed:
          self._buttonpressed.remove(aButton)
    except Exception as e:
      print(e)
      raise e

#--------------------------------------------------------
  def _cameraUD( self, aState, aDT ):
    ''' Handle camera state update '''

    rx = self._joydz(gamepad._RX)
    ry = self._joydz(gamepad._RY)

    panAngle = rx * 90.0
    tiltAngle = -ry * 90.0

    #Set camera pan/tilt values.
    pca.setangle(tank._CAMERAPAN, panAngle)
    pca.setangle(tank._CAMERATILT, tiltAngle)

#--------------------------------------------------------
  def _cameraIN( self, aState, aButton, aValue ):
    ''' Handle camera state input '''
    #Capture exceptions so we can print them because the gamepad driver catches and ignores
    # exceptions to control behaviour for controller issues.
    try:
      #If button pressed
      if aValue & 0x01:
        self._buttonpressed.add(aButton)
        if aButton == ecodes.BTN_A:
          self._lightbank.toggle()
        elif aButton == ecodes.BTN_X:
          self._strobe.toggle()
        elif aButton == ecodes.BTN_THUMBR:
          self.curstate = tank._HUMAN
      else: #Handle release events.
        if aButton == ecodes.BTN_Y:
          self.togglelights()

        #On release, make sure to remove button from pressed state set.
        if aButton in self._buttonpressed:
          self._buttonpressed.remove(aButton)
    except Exception as e:
      print(e)
      raise e

#--------------------------------------------------------
  def _movefwdUD( self, aState, aDT ):
    '''  '''
    lw = aState.get('lw')                       # Get left/right target distances.
    rw = aState.get('rw')
    done = 0

    self._left.update(aDT)                      # Update the distance values
    self._right.update(aDT)

    ld = self._left.dist                        # Get current distance values
    rd = self._right.dist

    #If left wheel hasn't reached target distance keep moving
    if (ld < lw):
      ls = .15
    else:
      ls = 0.0
      done += 1                                 # Inc done value to indicate left is done.

    self._left.speed(ls)                        # Set speed on left wheel.

    #If right wheel hasn't reached target distance keep moving.
    if rd < rw:
      rs = .15
    else:
      rs = 0.0
      done += 1                                 # Inc done value to indicate right is done.

    self._right.speed(rs)

    #If both wheels are done switch to human input state
    if done == 2:
      self.curstate = tank._HUMAN

#--------------------------------------------------------
  def _movefwdST( self, aState ):
    '''  '''
    amount = 100

    self._left.update(0)
    self._right.update(0)
    print('        ', end='\r')

    aState['lw'] = self._left.dist + amount
    aState['rw'] = self._right.dist + amount

#--------------------------------------------------------
  def run( self ):
    prevtime = perf_counter()
    try:
      while self.running:
        if self._haskeyboard and keyboard.is_pressed('q'):
          self._running = False
          print("quitting.")
        else:
          nexttime = perf_counter()
          prevtime = nexttime
          delta = min(max(0.01, nexttime - prevtime), _dtime)

          state.update(self.stateobj, delta)

          nexttime = perf_counter()
          sleeptime = _dtime - (nexttime - prevtime)  # 30fps - time we've already wasted.
          if sleeptime > 0.0:
            sleep(sleeptime)
    finally:
      pca.alloff()

#--------------------------------------------------------
if __name__ == '__main__':
  #If the startup button is on then start up.
  _startupswitch.update()
  if len(sys.argv) > 1 or (_startupswitch.on):
    t = tank()
    t.run()
