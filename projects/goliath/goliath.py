#!/usr/bin/env python3

import sys
import pca9685 as pca
import onestick
from gamepad import *
from esc import quicrun, surpass
from base import *
from wheel import *
from multiplex import *
from pin import *

from time import perf_counter, sleep
from buttons import button

#NOTE:
# A lot of Pin code has changed as well as main.py being renamed goliath.py.
#  Suggest updating everything. Also update and rebuild pca9685.
# Need to change evdev to run goliath.py instead of main.py
# Wrote the arm module but it isn't currently used

#--------------------------------------------------------
#PCA9685 pins:
_LTRACKPIN = 0                                  # left track motor
_RTRACKPIN = 1                                  # right track motor
_RISERSPD = 2
_PITCHSPD = 3

#--------------------------------------------------------
#RASPI pins:
_OMUX_0 = 18                                    # Output Multiplexer pins
_OMUX_1 = 23
_OMUX_2 = 24
_OMUX_3 = 25
_OMUX_S = 8

_IMUX_0 = 4                                     # Input Multiplexer pins
_IMUX_1 = 17
_IMUX_2 = 27
_IMUX_3 = 22
_IMUX_S = 10

_WAISTPIN = 5
_RISERB = 19                                    # Riser motor backward control pin
_PITCHB = 26                                    # Pitch motor backward control pin

#--------------------------------------------------------
#  MUX OUTPUT PINS:
#Currently these are raspi pins until I figure out how to get them to work.
#_WAISTPIN = 0                                 # OUTMUX Pin # for WAIST motor direction control
#_RISERF = 1                                   # Riser motor direction fwd
#_RISERB = 2                                   # Riser motor direction back
#_PITCHF = 3                                   # Pitch motor direction fwd
#_PITCHB = 4                                   # Pitch motor direction back
#   5 =
#   6 =
#   7 =
#   8 =
#   9 =
#   10 =
#   11 =
#   12 =
#   13 =
#   14 =
#   15 =

#--------------------------------------------------------
#  MUX INPUT PINS:
#   0 =
#   1 =
#   2 =
#   3 =
#   4 =
#   5 =
#   6 =
#   7 =
#   8 =
#   9 =
#   10 =
#   11 =
#   12 =
#   13 =
#   14 =
#   15 =

#--------------------------------------------------------
#Arm angle ranges:
#Almost all servos have a center at 45.
_LWRIST = (-30.0, 45.0, 110.0)  #ccw/cw
_LARMH = (35.0, 45.0, 57.0)     #L/R
_LARMV = (25.0, 45.0, 57.0)     #D/U

_RWRIST = (-30.0, 45.0, 110.0)  #ccw/cw
_RARMH = (52.0, 44.0, 35.0)     #L/R
_RARMV = (65.0, 45.0, 30.0)     #D/U

#--------------------------------------------------------
_dtime = .03
_startupswitch = button(16)
_DZ = 0.015                                   # Dead zone.
_MACADDRESS = '41:42:0B:90:D4:9E'             # Controller mac address

#--------------------------------------------------------
class goliath(object):
  ''' goliath '''
  _speedchange = 0.25
  _trackrate = 0.0

  ltrack, rtrack = range(2)                     # Indexes for _qs track controllers.

  #--------------------------------------------------------
  def __init__( self ):
    super(goliath, self).__init__()

    pca.startup()
    self._buttonpressed = set()                 # Create empty set to keep track of button press events.

    self._outmux = multiplex((_OMUX_0,_OMUX_1,_OMUX_2,_OMUX_3), _OMUX_S, multiplex.OUT)
    onestick.adjustpoints(_DZ)                  # Adjust onestick values to account for dead zone.

    rback = pin(_RISERB)
    self._riser = wheel(pca, _RISERSPD, rback)

    pback = pin(_PITCHB)
    self._pitch = wheel(pca, _PITCHSPD, pback)

    def qr( aIndex ):
      q = quicrun(pca, aIndex)
      #Set the change rate for the tracks to avoid jerking. 0.0 = none.
      q.rate = goliath._trackrate
      return q

    #left/right track controllers.
    self._qs = (
      qr(_LTRACKPIN),
      qr(_RTRACKPIN)
    )

    #Initialize the PS4 controller.
    self._controller = gamepad(_MACADDRESS, self._buttonaction)

    waistpin = pin(_WAISTPIN)
    self._waist = base(waistpin)

    self._speed = 1.0                           #speed scale for track motors.

    self._running = True

  def __del__( self ):
    pca.alloff()

  #--------------------------------------------------------
  @property
  def speed( self ):
    return self._speed

  #--------------------------------------------------------
  @speed.setter
  def speed( self, aValue ):
    self._speed = aValue
    self._qs[goliath.ltrack].scale = self._speed
    self._qs[goliath.rtrack].scale = self._speed

  #--------------------------------------------------------
  def _buttonaction( self, aButton, aValue ):
    '''  '''
    try:
      if aValue & 0x01:
        self._buttonpressed.add(aButton)
        if aButton == ecodes.BTN_TL:
          self._prevspeed()
        elif aButton == ecodes.BTN_TR:
          self._nextspeed()
      else: #Handle release events.
        #Add button checks here.

        #On release, make sure to remove button from pressed state set.
        if aButton in self._buttonpressed:
          self._buttonpressed.remove(aButton)
    except Exception as e:
      print(e)
      raise e

  #--------------------------------------------------------
  def _nextspeed( self ):
    ''' Increment speed value. '''
    self.speed = min(1.0, self.speed + goliath._speedchange)

  #--------------------------------------------------------
  def _prevspeed( self ):
    ''' Decrement speed value. '''
    self.speed = max(goliath._speedchange, self.speed - goliath._speedchange)

  #--------------------------------------------------------
  def _joy( self, aIndex ):
    ''' Get joystick value in range -1.0 to 1.0 '''
    v = self._controller.getjoy(aIndex)
    return v / 255.0

  #--------------------------------------------------------
  def joydz( self, aInput ):
    ''' Get joystick value and remove deadzone. '''

    v = self._joy(aInput)
    return v if abs(v) >= _DZ else 0.0

  #--------------------------------------------------------
  def updatetracks( self ):
    ''' Update the track speeds. '''

    #Convert joystick values from +/-255 to left/right track values.
    r, l = onestick.vels(-self.joydz(gamepad._LX), self.joydz(gamepad._LY))

    self._qs[goliath.ltrack].value = l
    self._qs[goliath.rtrack].value = r

  #--------------------------------------------------------
  def updatewaist( self ):
    ''' Update the wait rotation from joystick input. '''
    self._waist.speed = self.joydz(gamepad._RX)

  #--------------------------------------------------------
  def updateriser( self ):
    dir = 1.0 if ecodes.BTN_SELECT in self._buttonpressed else 0.0
    if ecodes.BTN_START in self._buttonpressed:
      dir -= 1
#     print('riser:', dir)

    self._riser.speed(dir)
#    self._pitch.speed(dir)

  #--------------------------------------------------------
  def updatepitch( self ):
    dir = self.joydz(gamepad._RY)
    self._pitch.speed(dir)

  #--------------------------------------------------------
  def run( self ):
    ''' Main loop to update inputs and outputs '''
    prevtime = perf_counter()
    try:
      while self._running:
        nexttime = perf_counter()
        delta = min(max(0.01, nexttime - prevtime), _dtime)
        prevtime = nexttime

        self._controller.update()
        self.updatetracks()
        self.updatewaist()
        self.updateriser()
        self.updatepitch()

        for q in self._qs:
          q.update(delta)

        nexttime = perf_counter()
        sleeptime = _dtime - (nexttime - prevtime)  # 30fps - time we've already wasted.
        if sleeptime > 0.0:
          sleep(sleeptime)
    except Exception as ex:
      print(ex)
      raise ex
    finally:
      pca.alloff()

#--------------------------------------------------------
if __name__ == '__main__':
  #If the startup button is on then start up.
  _startupswitch.update()
  if len(sys.argv) > 1 or (_startupswitch.on):
    s = goliath()
    s.run()
