#!/usr/bin/env python3
# 08/22/2020 10:50 AM

# sudo apt install rpi.gpio

import sys
from gamepad import *
from wheel import *
from strobe import *
import state

import pca9865 as pca
import onestick

from time import perf_counter, sleep
from buttons import gpioinit, button
import keyboard

gpioinit() # Initialize the GPIO system so we may use the pins for I/O.

_dtime = .03
_startupswitch = button(16)

#--------------------------------------------------------
def deadzone( aValue, aLimit ):
  return aValue if abs(aValue) >= aLimit else 0.0

#--------------------------------------------------------
class tank(object):

  _MACADDRESS = '41:42:E4:57:3E:9E'              # Controller mac address
  _HEADLIGHTS = (0, 1)
  _TAILLIGHTS = (2, 3)
  _SPEEDPINL = 27
  _SPEEDPINR = 22
  _DZ = 0.015                                    # Dead zone.

  _HUMAN, _TURNING, _MOVEFWD = range(3)

  _speedchange = 0.25

#--------------------------------------------------------
  def __init__( self ):

    pca.startup()
    self._gpmacaddress = '' #'E4:17:D8:2C:08:68'
    self._buttonpressed = set()                 # A set used to hold button pressed states, used for debounce detection and button combos. #
    self._left = wheel(pca, 8, 9, 10, tank._SPEEDPINL)
    self._left.name = 'lw'
    self._right = wheel(pca, 4, 6, 5, tank._SPEEDPINR)
    self._right.name = 'rw'
    self._lights = 0.0
    self._onestick = False

    #Initialize the states.
    self._states = {}
    self._states[tank._HUMAN] = state.create(u = self._humanUD, i = self._humanIN)
    self._states[tank._TURNING] = state.create()
    self._states[tank._MOVEFWD] = state.create(s = self._movefwdST, u = self._movefwdUD)
    self._curstate = tank._HUMAN

    self._strobe = strobe(pca, 15, 14)
    self.togglelights()
    onestick.adjustpoints(tank._DZ)             # Set point to minimum value during interpretation.

    self._controller = gamepad(tank._MACADDRESS, self._buttonaction)

    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

    self._running = True

#--------------------------------------------------------
  def __del__( self ):
    pca.alloff()

#--------------------------------------------------------
  @property
  def running( self ): return self._running

#--------------------------------------------------------
  @property
  def curstate( self ):
    return self._states[self._curstate]

#--------------------------------------------------------
  def _buttonaction( self, aButton, aValue ):
    '''Callback function for controller.'''
    state.input(self.curstate, aButton, aValue)

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
    wheel.changegear(tank._speedchange)

#--------------------------------------------------------
  def _prevspeed( self ):
    ''' Decrement speed value. '''
    wheel.changegear(-tank._speedchange)

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
  def _setstate( self, aState ):
    '''  '''
    try:
      if self._curstate != aState:
        state.end(self.curstate)
        self._curstate = aState
        state.start(self.curstate)
    except Exception as e:
      print(e)
      raise e

#--------------------------------------------------------
  def _humanUD( self, aState, aDT ):
    ''' Update method for human control state. '''
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
    print('        ', end='\r')

#--------------------------------------------------------
  def _humanIN( self, aState, aButton, aValue ):
    '''  '''
    #Capture expections so we can print them because the gamepad driver catches and ignores
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
        elif aButton == ecodes.BTN_X:
          self._strobe.on = not self._strobe.on
        elif aButton == gamepad.BTN_DPADU:
          self._setstate(tank._MOVEFWD)
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
  def _movefwdUD( self, aState, aDT ):
    '''  '''
    lw = aState.get('lw')
    rw = aState.get('rw')
    moving = 2

    self._left.update(aDT)
    self._right.update(aDT)
    print('        ', end='\r')
    ld = self._left.dist
    rd = self._right.dist

    print(ld, lw, rd, rw)
    if (ld < lw):
      self._left.speed(.15)
      moving -= 1

    if rd < rw:
      self._right.speed(.15)
      moving -= 1

    if moving == 2:
      self._setstate(tank._HUMAN)

#--------------------------------------------------------
  def _movefwdST( self, aState ):
    '''  '''
    self._left.update(0)
    self._right.update(0)
    print('        ', end='\r')

    aState['lw'] = self._left.dist + 30
    aState['rw'] = self._right.dist + 30

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
          delta = max(0.01, nexttime - prevtime)
          prevtime = nexttime
          if delta > _dtime:
            delta = _dtime

          self._strobe.update(delta)
          self._controller.update()
          state.update(self.curstate, delta)

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
