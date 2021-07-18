#!/usr/bin/env python3

import sys
import pca9685 as pca
import adc
import onestick
import state
import oled
from gamepad import *
from esc import quicrun, surpass
from base import *
from wheel import *
from multiplex import *
from pin import *
from fuelgauge import *
from arm import *

from time import perf_counter, sleep
from buttons import button

#NOTE:
#DONE: Fuel gauge needs to read and only trigger if value stays consistently below the desired value for a given amount of time.
#DONE: Write code to control the claws from the triggers.
#DONE: Set dpad u/d to control the riser.
#DONE: Extension code. Extension center = 0.54, full rev = 1.0, full fwd = 0.0
#May need to update wheels even when in non-drive state to make sure they get correctly turned off.
# Perhaps the end state should last until they report stopped.
#DONE: Add oled display. Must include oled shared lib and compile.
#DONE: Add code to open claws for 1/4 second on startup.

#Double Click
#DPAD L - change state on l-stick
#  State 0: drive
#  State 1: larm movement
#           l thumb down - larm wrist/extend
#DPAD R - change state on r-stick
#  State 0: body
#  State 1: rarm movement
#           r thumb down - larm wrist/extend

#diamond+X = arm
#triangle+circle = disarm

#shoulder+trigger = weapon fire
#dpad u/d = riser


#--------------------------------------------------------
#PCA9685 pins:
_LTRACKPIN = 0                                  # left track motor
_RTRACKPIN = 1                                  # right track motor
_RISERSPD = 2
_PITCHSPD = 3
_LARMVPCA = 4
_LARMHPCA = 5
_LARMEPCA = 6
_LARMWPCA = 7
_LCLAWPCA = 8
_RARMVPCA = 9
_RARMHPCA = 10
_RARMEPCA = 11
_RARMWPCA = 12
_RCLAWPCA = 13
#14
#15

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
#Almost all servos have a center at 45
_ARMENTRIES = 8
_GROUP = 50
_LARMH, _LARMV, _LARMW, _LARME, _RARMH, _RARMV, _RARMW, _RARME = range(_ARMENTRIES)

#Array of ranges
_RANGE = [(0.0, 12.0, 25.0),                    # L/R
          (30.0, 10.0, -20.0),                  # D/U
          (90.0, 0.0, -70.0),                   # ccw/cw
          (1.0, 0.54, 0.0),                     # Extension
          (0.0, 12.0, 25.0),                    # L/R
          (-3.0, 15.0, 45.0),                   # D/U
          (87.0, 10.0, -70.0),                  # ccw/cw
          (1.0, 0.54, 0.0)                      # Extension
          ]

#--------------------------------------------------------
#Button flags
_DBL = 0x1000                                   # Flag set on the button even value to indicate double tap timing
_DBLTIME = 0.15                                 # Time in seconds between press/release/press to get a double tap

#--------------------------------------------------------
_dtime = .1
_startupswitch = button(16)
_DZ = 0.015                                     # Controller analog stick dead zone
_MACADDRESS = '41:42:0B:90:D4:9E'               # Controller mac address
_MINVOLTS = 11.1                                # Minimum battery voltage before shutdown
_LOWVOLTTIME = 10.0                             # Time in seconds battery voltage must be below threshold before reporting low

#--------------------------------------------------------
class goliath(object):
  ''' goliath '''
  _trackrate = 0.0

  ltrack, rtrack = range(2)                     # Indexes for _qs track controllers.

  #--------------------------------------------------------
  def __init__( self ):
    super(goliath, self).__init__()

    oled.startup()
    oled.setrotation(2)

    self._buttonpressed = {}                    # Create empty dict to keep track of button press events.
                                                # Key = btn:, Item = value

    onestick.adjustpoints(_DZ)                  # Adjust onestick values to account for dead zone.

    self._adc = adc.create(0x48)
    fuelpin = adc.adcpin(self._adc, 4)          # Read pin 0 of adc
    self._fuel = fuelgauge(fuelpin, _MINVOLTS, _LOWVOLTTIME)

    rback = pin(_RISERB)
    self._riser = wheel(pca, _RISERSPD, rback)

    pback = pin(_PITCHB)
    self._pitch = wheel(pca, _PITCHSPD, pback)

    self._arms = [None] * _ARMENTRIES
    self._armdirs = [0.0] * _ARMENTRIES

    #Actions possible for left/right stick input.
    self._drivestate = state.create(u = self._driveUD, i = self._driveINPUT, e = self._driveEND)
    self._larmstate = state.create(u = self._larmUD, i = self._larmINPUT)
    self._larmstate[_GROUP] = 0        #Arm has 2 groups. 0 = shoulder, 1 = wrist/extent
    self._lstate = self._drivestate

    #Actions possible for left/right stick input.
    self._bodystate = state.create(u = self._bodyUD, i = self._bodyINPUT, e = self._bodyEND)
    self._rarmstate = state.create(u = self._rarmUD, i = self._rarmINPUT)
    self._rarmstate[_GROUP] = 0        #Arm has 2 groups. 0 = shoulder, 1 = wrist/extent
    self._rstate = self._bodystate

    self._arms[_LARMH] = arm(pca, _LARMHPCA, 1.75, _RANGE[_LARMH])
    self._arms[_LARMV] = arm(pca, _LARMVPCA, 0.75, _RANGE[_LARMV])
    self._arms[_LARMW] = arm(pca, _LARMWPCA, 10.0, _RANGE[_LARMW])
    self._arms[_LARME] = extension(pca, _LARMEPCA, _RANGE[_LARME])

    self._arms[_RARMH] = arm(pca, _RARMHPCA, 1.75, _RANGE[_RARMH])
    self._arms[_RARMV] = arm(pca, _RARMVPCA, 0.75, _RANGE[_RARMV])
    self._arms[_RARMW] = arm(pca, _RARMWPCA, 10.0, _RANGE[_RARMW])
    self._arms[_RARME] = extension(pca, _RARMEPCA, _RANGE[_RARME])

    self._lclaw = surpass(pca, _LCLAWPCA)
    self._rclaw = surpass(pca, _RCLAWPCA)

    self._lclaw.speed = -1.0
    self._rclaw.speed = 1.0

    #Open claws for 1/4 second.
    prevtime = perf_counter()
    endtime = prevtime + 0.5
    while prevtime < endtime:
      nexttime = perf_counter()
      delta = nexttime - prevtime
      prevtime = nexttime
      self._lclaw.update(delta)
      self._rclaw.update(delta)

    self._lclaw.speed = 0.0
    self._rclaw.speed = 0.0

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

  #--------------------------------------------------------
  def __del__( self ):
    self._shutdown()

  #--------------------------------------------------------
  def _shutdown( self ):
    ''' Shutdown everything. '''
    pca.alloff()
#    adc.release(self._adc)
    pca.shutdown()
    oled.shutdown()

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
  @property
  def lstate( self ):
    return self._lstate

  #--------------------------------------------------------
  @lstate.setter
  def lstate( self, aValue ):
    self._lstate = state.switch(self._lstate, aValue)

  #--------------------------------------------------------
  @property
  def rstate( self ):
    return self._rstate

  #--------------------------------------------------------
  @rstate.setter
  def rstate( self, aValue ):
    self._rstate = state.switch(self._rstate, aValue)

  #--------------------------------------------------------
  def _buttonaction( self, aButton, aValue ):
    ''' Process button actions. '''
    try:
      pv, pt = self._buttonpressed.get(aButton, (0, 0.0))
      now = perf_counter()

      if aValue & 0x01:
        #If prev state was off and time interval short enough then set dbl flag
        if ((pv & 0x01) == 0) and (now - pt < _DBLTIME):
          aValue |= _DBL
      else: #Handle release events
        #If prev state was pressed and time is short enough, set dbl flag
        if (pv & 0x01):
          if (now - pt < _DBLTIME):
            aValue |= _DBL

      #See if left/right states consume button action
      handled = state.input(self.lstate, aButton, aValue)
      if not handled:
        handled = state.input(self.rstate, aButton, aValue)
        if not handled:
          dir = 1.0 if (aValue & 0x01) else -1.0
          if aButton == gamepad.BTN_DPADU:
            self._riser.speed += dir
          elif aButton == gamepad.BTN_DPADD:
            self._riser.speed -= dir
          elif aButton == ecodes.BTN_TR:
            self._rclaw.speed -= dir
          elif aButton == ecodes.BTN_TR2:
            self._rclaw.speed += dir
          elif aButton == ecodes.BTN_TL:
            self._lclaw.speed += dir
          elif aButton == ecodes.BTN_TL2:
            self._lclaw.speed -= dir


       #Save the button state into the map
      self._buttonpressed[aButton] = (aValue, now)

    #Have to capture and output exceptions here as this code
    # returns to a C++ library which will not pass the exception back to python
    except Exception as e:
      print(e)
      raise e

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
  def _driveUD( self, aState, aDT ):
    ''' Update the track speeds. '''

    #Convert joystick values from +/-255 to left/right track values.
    r, l = onestick.vels(-self.joydz(gamepad._LX), self.joydz(gamepad._LY))

    self._qs[goliath.ltrack].value = l
    self._qs[goliath.rtrack].value = r

    for q in self._qs:
      q.update(aDT)

  #--------------------------------------------------------
  def _driveINPUT( self, aState, aButton, aValue ):
    ''' Handle drive state input. '''

    handled = False
    if aValue & 0x01:
      if aButton == gamepad.BTN_DPADL:
        handled = True
        self.lstate = self._larmstate           # Change state to larm control

    return handled

  #--------------------------------------------------------
  def _driveEND( self, aState ):
    ''' End drive state by shutting down tracks. '''
    self._qs[goliath.ltrack].stop()
    self._qs[goliath.rtrack].stop()

    for q in self._qs:
      q.update(0.1)

  #--------------------------------------------------------
  def _bodyUD( self, aState, aDT ):
    ''' Update the waist rotation and pitch from joystick input. '''
    x = self.joydz(gamepad._RX)
    y = self.joydz(gamepad._RY)
    self._waist.speed = x
    self._pitch.speed = y

  #--------------------------------------------------------
  def _bodyINPUT( self, aState, aButton, aValue ):
    ''' Handle body state input. '''

    handled = False

    if aValue & 0x01:
      if aButton == gamepad.BTN_DPADR:
        handled = True
        self.rstate = self._rarmstate           # Change state to rarm control

    if not handled:
      dir = 0.0
      bset = False
      if aButton == ecodes.BTN_START:
        dir -= 1.0 if (aValue & 0x01) else -1.0
        bset = True
        handled = True
      elif aButton == ecodes.BTN_SELECT:
        dir += 1.0 if (aValue & 0x01) else -1.0
        bset = True
        handled = True

      if bset:
        self._riser.speed += dir

    return handled

  #--------------------------------------------------------
  def _bodyEND( self, aState ):
    ''' End body state by shutting down motors. '''
    self._waist.speed = 0.0
    self._pitch.speed = 0.0

  #--------------------------------------------------------
  def _larmUD( self, aState, aDT ):
    ''' Control left arm movement. '''

    x = self.joydz(gamepad._LX)
    y = self.joydz(gamepad._LY)

    if aState[_GROUP] == 0:
      self._arms[_LARMH].update(x * aDT)
      self._arms[_LARMV].update(y * aDT)
    else:
      self._arms[_LARMW].update(x * aDT)
      self._arms[_LARME].speed = y

  #--------------------------------------------------------
  def _larmINPUT( self, aState, aButton, aValue ):
    ''' Handle left arm control0 state input. '''

    handled = False
    #If pressed
    if aValue & 0x01:
      #If lthumb switch control group
      if aButton == ecodes.BTN_THUMBL:
        handled = True
        #Change state to larm0state
        aState[_GROUP] = 1 - aState[_GROUP]
      elif aButton == gamepad.BTN_DPADL:
        handled = True
        self.lstate = self._drivestate          # Change state to drive

    return handled

  #--------------------------------------------------------
  def _rarmUD( self, aState, aDT ):
    ''' Control right arm movement. '''

    x = -self.joydz(gamepad._RX)
    y = -self.joydz(gamepad._RY)

    if aState[_GROUP] == 0:
      self._arms[_RARMH].update(x * aDT)
      self._arms[_RARMV].update(y * aDT)
    else:
      self._arms[_RARMW].update(x * aDT)
      self._arms[_RARME].speed = y

  #--------------------------------------------------------
  def _rarmINPUT( self, aState, aButton, aValue ):
    ''' Handle right arm control0 state input. '''

    handled = False
    #If pressed
    if aValue & 0x01:
      #If rthumb switch control group
      if aButton == ecodes.BTN_THUMBR:
        handled = True
        #Change control group
        aState[_GROUP] = 1 - aState[_GROUP]
      elif aButton == gamepad.BTN_DPADR:
        handled = True
        self.rstate = self._bodystate           # Change state to body

    return handled

  #--------------------------------------------------------
  def run( self ):
    ''' Main loop to update inputs and outputs '''

    prevtime = perf_counter()
    try:
      while self._running:
        nexttime = perf_counter()
        delta = min(max(0.001, nexttime - prevtime), _dtime)
#        delta = 0.03
        prevtime = nexttime
#         print(delta)
        if self._fuel.update(delta) == False:
          self._running = False
          print('Battery is at', self._fuel.volts, 'Recharge!')
          oled.text((0, 12), 'Shutting Down!')
        oled.text((0, 0), f'Bat: {self._fuel.volts:.2f}v')

        self._controller.update()
        state.update(self._lstate, delta)
        state.update(self._rstate, delta)

        #Update the claw escs
        self._lclaw.update(delta)
        self._rclaw.update(delta)

        oled.display()

        nexttime = perf_counter()
        sleeptime = _dtime - (nexttime - prevtime)  # 30fps - time we've already wasted.
#        print(sleeptime)
        if sleeptime > 0.0:
          sleep(sleeptime)
    except Exception as ex:
      print(ex)
      raise ex
    finally:
      self._shutdown()

#--------------------------------------------------------
if __name__ == '__main__':
  #If the startup button is on then start up.
  _startupswitch.update()
  if len(sys.argv) > 1 or (_startupswitch.on):
    s = goliath()
    s.run()
