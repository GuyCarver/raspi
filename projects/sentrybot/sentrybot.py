#!/usr/bin/env python3

from pca9865 import *
from quicrun import *
from gamepad import *
from sound import *
import settings

import saveload
import ps2con

class sentrybot(object):
  '''docstring for sentrybot'''

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

  _startupsound = 'powerup'

  def __init__( self ):
    self._controllernum = 0                     #Type of controller 0=FC30, 1=ps2
    self._controller = None                     #Start out with no controller. Will set once we no which type.
    self._speed = 100.0
    self._accel = 50.0
    #todo: load settings json
    self.load()

#    #todo: Take out once it's done in settings load.
#    self.controller = 0

    self._running = True

    sound.start()                               #Start the sound event listener

    #Start settings server
    self._settingsthread = Thread(target=lambda: settings.run(self))


  __del__( self ):
    self.save()
    self._contoller = None

  @property
    def running( self ): return self._running

  @property
  def speed( self ):
    return self._speed

  @speed.setter
  def speed( self, aValue ):
    self._speed = aValue

  @property
  def accel( self ):
    return self._accel

  @accel.setter
  def accel( self, aValue ):
    self._accel = aValue

  @property
  def buttonsounds( self ):
    return sentrybot._buttonsounds

  @property
  def startupsound( self ):
    return sentrybot._startupsound

  @startupsound.setter
  def startupsound( self, aValue ):
    sentrybot._startupsound = aValue

  def btntoname( self, aButton ):
    '''Abstraction interface for access to gamepad.btntoname()'''
    return gamepad.btntoname(aButton)

  def setbuttonsound( self, aButton, aFile ):
    '''Assign given sound by name to given button name.'''

    #NOTE: We create a new sound object for each call.
    # But if the same file is used for multiple buttons we
    # don't use the same sound object. Not worrying about that
    # because each button should be assigned a different sound anyway.
    btnnum = gamepad.nametobtn(aButton)
    if aFile:
      aFile = sound(aFile)
    sentrybot._buttonsounds[btnnum] = aFile

  @property
  def controller( self ): return self._controllernum

  @controller.setter
  def controller( self, aValue ):
    '''Set the controller # and create the associated controller if necessary'''
    #Don't do anything if already set to the current value.
    if self._controllernum != aValue or self._controller == None:
      self._controller = aValue
      if aValue:
        self._controller = ps2con.ps2con(27, 22, 18, 17, self._ps2action)
      else:
        self._controller = gamepad(aCallback = self._buttonaction)

  def initsounds( self, aSounds ):
    '''Temporary method to initialize sounds from a list of button, group, sound'''
    for s in aSounds:
      b = gamepad.nametobtn(s[0])               #Turn button name into button #.
      if b >= 0:
        sentrybot._buttonsounds[s[0]] = sound(s[2] + '.mp3', s[1], self._sounddone)

  def _sounddone( self, aSound ):
    '''Callback function when sound file is done playing.'''
#    print('Done:', aSound.source)
    pass

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

  def run( self ):
    '''Main loop to run the robot.'''
    s = sound(self.startupsound + '.mp3')
    s.play()
    while self.running:
      if self._controller:
        self._controller.update()
      sound.update()                            #Update sound event listener
      sleep(0.03)                               #Update 3fps

if __name__ == '__main__':
  sentry = sentrybot()
  sentry.run()

