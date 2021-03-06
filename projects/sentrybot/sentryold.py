#!/usr/bin/env python3

from pca9685 import *
from quicrun import *
from gamepad import *
from sound import *
from settings import *
from atom import *

import angle
import body
import saveload
import ps2con
import legs

from threading import Thread #,Lock
from time import perf_counter, sleep
import keyboard

#todo: Remove testing flag from settings server creation.

def deadzone( aValue, aLimit ):
  return aValue if abs(aValue) >= 0.01 else 0.0

#------------------------------------------------------------------------
class sentrybot(object):

  #map of button to sound object.  This is loaded from a json file.
  _buttonsounds = {
    ecodes.BTN_A : None,
    ecodes.BTN_B : None,
    ecodes.BTN_C : None,
    ecodes.BTN_X : None,
    ecodes.BTN_Y : None,
    ecodes.BTN_SELECT : None,
    ecodes.BTN_START : None,
    ecodes.BTN_TL2 : None,
    ecodes.BTN_TR2 : None,
    ecodes.BTN_TL : None,
    ecodes.BTN_TR : None,
    ecodes.BTN_THUMBL : None,
    ecodes.BTN_THUMBR : None,
    gamepad.BTN_DPADU : None,
    gamepad.BTN_DPADR : None,
    gamepad.BTN_DPADD : None,
    gamepad.BTN_DPADL : None
  }

  #map of ps2 cotnroller buttons to 8Bitdo FC30 Pro retro controller buttons.
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

  _ps2joymap = {
    gamepad._LX : ps2con.LX,
    gamepad._LY : ps2con.LY,
    gamepad._RX : ps2con.RX,
    gamepad._RY : ps2con.RY,
  }

  def __init__( self ):
    self._controllernum = 0                     #Type of controller 0=FC30, 1=ps2
    self._controller = None                     #Start out with no controller. Will set once we no which type.
    self._startupsound = None
    self._rotx = 0.0
    self._roty = 0.0
    self._rate = 90.0
    self.armangle = 0.0
    self.invert = False
    self._pca = pca9685()

    self.load()                                 #load settings json

    #If no keyboard we'll get an exception here so turn off keyboard flag.
    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

    self._running = True

    sound.start()                               #Start the sound event listener

    #Start settings server, 2nd param True if testing html page.
    self._settingsthread = Thread(target=lambda: settings.run(self, True))

  def __del__( self ):
    self.save()
    self._contoller = None

  @property
  def partdata( self ): return body._initdata

  @property
  def running( self ): return self._running

  @property
  def rate( self ):
    return self._rate

  @rate.setter
  def rate( self, aValue ):
    self._rate = aValue

  @property
  def buttonsounds( self ):
    return sentrybot._buttonsounds

  @property
  def startupsound( self ):
    return self._startupsound

  @startupsound.setter
  def startupsound( self, aFile ):
    if aFile != None:
      aFile = sound(aFile) if (aFile != 'None') else None
    self._startupsound = aFile

  @property
  def armangle( self ):
    return self._armangle

  @armangle.setter
  def armangle( self, aValue ):
    self._armangle = aValue
    self._cossinl = angle.cossin(aValue)
    self._cossinr = angle.cossin(aValue)

  @property
  def invert( self ):
    return self._invert > 0.0

  @invert.setter
  def invert( self, aValue ):
    self._invert = -1.0 if aValue else 1.0

  def btntoname( self, aButton ):
    '''Abstraction interface for access to gamepad.btntoname()'''
    return gamepad.btntoname(aButton)

  def previewsound( self, aFile ):
    #NOTE: May need to kick this off in the main thread and just queue it here.
    snd = sound(aFile, 10)             #Group 10.
    snd.play()

  def setbuttonsound( self, aButton, aFile ):
    '''Assign given sound by name to given button name.'''

    #NOTE: We create a new sound object for each call.
    # But if the same file is used for multiple buttons we
    # don't use the same sound object. Not worrying about that
    # because each button should be assigned a different sound anyway.
    if aButton == 'startup':
#      print('setting startup to', aFile)
      self.startupsound = aFile
    else:
      btnnum = gamepad.nametobtn(aButton)
      if aFile:
        aFile = sound(aFile) if (aFile != 'None') else None
      sentrybot._buttonsounds[btnnum] = aFile

  @property
  def controller( self ): return self._controllernum

  @controller.setter
  def controller( self, aValue ):
    '''Set the controller #.'''
    self._controllernum = aValue
#    print('Controller:', self._controllernum)

  def _initcontroller( self ):
    '''Create the controller if necessary.'''
    if self._controllernum:
#      print('starting ps2 controller')
      self._controller = ps2con.ps2con(27, 22, 18, 17, self._ps2action)
    else:
#      print('starting Retro Controller')
      self._controller = gamepad(aCallback = self._buttonaction)

  def setcontroller( self, aIndex ):
    '''Set controller index if it changed, and create a controller.'''
    if self._controllernum != aIndex or self._controller == None:
      self.controller = aIndex
      self._initcontroller()

  def initsounds( self, aSounds ):
    '''Temporary method to initialize sounds from a list of button, group, sound'''
    for s in aSounds:
      b = gamepad.nametobtn(s[0])               #Turn button name into button #.
      if b >= 0:
        sentrybot._buttonsounds[b] = sound(s[2], s[1], self._sounddone)

  def _sounddone( self, aSound ):
    '''Callback function when sound file is done playing.'''
#    print('Done:', aSound.source)
    pass

  def partrate( self, aIndex ):
    '''Get rate for given part.'''
    p = body.getpart(aIndex)
    return p.rate if p else 0.0

  def partminmax( self, aIndex ):
    '''Get min/max for given part.'''
    p = body.getpart(aIndex)
    return p.minmax if p else (0.0, 100.0)

  def partdefminmax( self, aIndex ):
    '''Get min/max for given part.'''
    p = body.getpart(aIndex)
    return p._defminmax if p else (-100.0, 100.0)

  def setpartdata( self, aIndex, aRate, aMinMax ):
    '''Set the rate and min/max values for given part.'''
    p = body.getpart(aIndex)
    if p:
      p.rate = aRate
      p.minmax = aMinMax

  def _joy( self, aIndex ):
    '''Get joystick value in range 0.0-100.0'''
    if self._controllernum == 1:
      aIndex = self._ps2joymap[aIndex]

    return self._controller.getjoy(aIndex) / 255.0

  def _ps2action( self, aButton, aValue ):
    '''Callback for ps2 button events. They are remapped to FC30 events and sent
       to the _buttonaction callback.'''
    if aValue == 0x03:
      k = sentrybot._ps2map[aButton]
#     print(aButton, aValue, k)
      self._buttonaction(k, aValue)

  def _buttonaction( self, aButton, aValue ):
    '''Callback function for nintendo controller.'''
    if aValue & 0x01:
      s = sentrybot._buttonsounds[aButton]
      if s != None:
        s.play()
#        print('playing', s.source)
    elif aButton == gamepad.GAMEPAD_DISCONNECT:
      print('Disconnected controller!')

  def save( self ):
    '''Do save of properites.'''
    saveload.saveproperties(self)

  def load( self ):
    '''Do load of properties.'''
    saveload.loadproperties(self)

  def _initparts( self ):
    body.initparts(self._pca)

  def _updateparts( self, aDelta ):
    '''Update all servos based on joystick input'''

    rx = -self._joy(gamepad._RX)                #Negate cuz servo is backwards.
    ry = self._joy(gamepad._RY) * self._invert
    rx = deadzone(rx, 0.01)
    ry = deadzone(ry, 0.01)

    lx = self._joy(gamepad._LX)
    lx = deadzone(lx, 0.01)
    ly = self._joy(gamepad._LY)
    ly = deadzone(ly, 0.01)

    if self._rate > 0.0:
      if aDelta != 0.0:
        d = self._rate * aDelta
        v = self._rotx + (rx * d)
        self._rotx = min(max(v, -90.0), 90.0)
        v = self._roty + (ry * d)
        self._roty = min(max(v, -90.0), 90.0)
    else:
      v = rx * 90.0
      self._rotx = min(max(v, -90.0), 90.0)
      v = ry * 90.0
      self._roty = min(max(v, -90.0), 90.0)

#    print(self._rotx, self._roty, '                ', end='\r')
#    print(rx, ry, '                ', end='\r')

    #todo: Figure out how to disperse right stick movement into torso, head and arms.

    t = body.getpart(body._TORSO)
    t.value = self._rotx / 8.0
    hh = body.getpart(body._HEAD_H)
    hh.value = -self._rotx / 4.0
    hv = body.getpart(body._HEAD_V)
    hv.value = -self._roty
#    print('hh: ', hh.value, '        ', end='\r')
#    print('hv: ', hv.value, '        ', end='\r')

    rarmh = body.getpart(body._RARM_H)
    rarmv = body.getpart(body._RARM_V)
    larmh = body.getpart(body._LARM_H)
    larmv = body.getpart(body._LARM_V)

    #Rotate x,y by angle and apply to arms.
    armx, army = angle.rotate((self._rotx, -self._roty), self._cossinl)
    larmh.value = (armx)
    larmv.value =(army)

    armx, army = angle.rotate((self._rotx, self._roty), self._cossinr)
    rarmh.value = (armx)
    rarmv.value = (army)

    #todo: Update gun servo based on a button input.

#    vl, vr = legs.vels(lx, ly)
    vl = ly
    vr = ry
    lleg = body.getpart(body._LLEG)
    rleg = body.getpart(body._RLEG)

#    print(vl, '    ', end='\r')
    lleg.speed = vl * lleg.maxspeed
    rleg.speed = vr * rleg.maxspeed

    lleg.update(aDelta)
    rleg.update(aDelta)

  def run( self ):
    '''Main loop to run the robot.'''
    self._settingsthread.start()
    if self.startupsound != None:
      self.startupsound.play()

    #Save init of parts and controller until last second to ensure
    # they get updates as quickly as possible after update.
    self._initparts()
    self._initcontroller()

    prevtime = perf_counter()

    try:
      while self.running:
        if self._haskeyboard and keyboard.is_pressed('q'):
          self._running = False
          print("quitting.")
        else:
          nexttime = perf_counter()
          delta = max(0.001, nexttime - prevtime)
          prevtime = nexttime

          if self._controller:
            self._controller.update()
          self._updateparts(delta)
          sound.update()                          #Update sound event listener

          #Get how much time has passed since beginning of frame and subtract
          # that from the sleep time.
          nexttime = perf_counter()
          delta = nexttime - prevtime

          sleep(max(0.01, 0.03 - delta))         #Update 30fps
    except Exception as e:
      body.off()                                #Make sure motors and servos are off.
      c = sound('corrupt')                      #Play corruption audio.
      c.play()
      raise e

#------------------------------------------------------------------------
if __name__ == '__main__':
  sentry = sentrybot()
  sentry.run()

