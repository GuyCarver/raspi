#!/usr/bin/env python3

from pca9865 import *
from quicrun import *
from gamepad import *
from sound import *

import ps2con

#temporary button, group, sound-name mappings.  Move to json.
mysounds = (
  (ecodes.BTN_A, 1, 'alertsafety'),
  (ecodes.BTN_B, 1, 'alertsecurity'),
  (ecodes.BTN_C, 1, 'allcitizenscalm'),
  (ecodes.BTN_X, 1, 'donotinterfere'),
  (ecodes.BTN_Y, 1, 'hostiledetected2'),
  (ecodes.BTN_SELECT, 1, 'hostiles'),
  (ecodes.BTN_START, 1, 'movealong'),
  (ecodes.BTN_TL2, 1, 'nohostiles'),
  (ecodes.BTN_TR2, 1, 'noncombatants'),
  (ecodes.BTN_TL, 1, 'privateproperty'),
  (ecodes.BTN_TR, 1, 'systemreport'),
  (ecodes.BTN_THUMBL, 1, 'warningleave'),
  (ecodes.BTN_THUMBR, 1, 'warningsecurity'),
  (gamepad.BTN_DPADU, 2, 'warningviolation'),
  (gamepad.BTN_DPADR, 2, 'weaponsfree'),
  (gamepad.BTN_DPADD, 2, 'weaponslocked'),
  (gamepad.BTN_DPADL, 2, 'startup')
)

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

  def __init__( self ):
    self._controllernum = 0                     #Type of controller 0=FC30, 1=ps2
    self._controller = None                     #Start out with no controller. Will set once we no which type.
    #todo: load settings json
    self._initsounds()
    #todo: start settings server

    #todo: Take this out once it's done in settings load.
    self.controller = 0

    self._running = True
    sound.start()                               #Start the sound event listener

  @property
  def controller( self ): return self._controllernum

  @controller.setter
  def controller( self, aValue ):
    '''Set the controller # and create the associated controller if necessary'''
    if self._controllernum != aValue or self._controller == None:
      self._controller = aValue
      if aValue:
        self._controller = ps2con.ps2con(27, 22, 18, 17, self._ps2action)
      else:
        self._controller = gamepad(aCallback = self._buttonaction)

  def _initsounds( self ):
    '''Temporary method to initialize sounds from a list of button, group, sound'''
    for s in mysounds:
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

  def run( self ):
    '''Main loop to run the robot.'''
    s = sound('powerup.mp3')
    s.play()
    while self._running:
      if self._controller:
        self._controller.update()
      sound.update()                            #Update sound event listener
      sleep(0.03)                               #Update 3fps

if __name__ == '__main__':
  sentry = sentrybot()
  sentry.run()

