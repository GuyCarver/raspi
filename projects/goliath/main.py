#!/usr/bin/env python3

import sys
import pca9865 as pca
import onestick
from gamepad import *
from quicrun import *
from base import *
from wheel import *

from time import perf_counter, sleep
from buttons import gpioinit, button

gpioinit() # Initialize the GPIO system so we may use the pins for I/O.

_dtime = .03
_startupswitch = button(16)

#--------------------------------------------------------
class goliath(object):
  """goliath2"""
  _DZ = 0.015                                   # Dead zone.
  _WAISTPIN = 18                                # Pin # for WAIST motor direction control
  _LTRACKPIN = 0                                # PCA pin index for left track motor.
  _RTRACKPIN = 1                                # PCA pin index for right track motor.
  _MACADDRESS = '41:42:0B:90:D4:9E'             # Controller mac address
  _speedchange = 0.25
  _trackrate = 0.0

  ltrack, rtrack = range(2)                     # Indexes for _qs track controllers.

#--------------------------------------------------------
  def __init__( self ):
    super(goliath, self).__init__()

    pca.startup()
    self._buttonpressed = set()                 # Create empty set to keep track of button press events.

    onestick.adjustpoints(goliath._DZ)          # Adjust onestick values to account for dead zone.
    self._riser = wheel(pca, 8, 10, 9)
    self._pitch = wheel(pca, 12, 13, 14)

    def qr( aIndex ):
      q = quicrun(pca, aIndex)
      #Set the change rate for the tracks to avoid jerking. 0.0 = none.
      q.rate = goliath._trackrate
      return q

    #left/right track controllers.
    self._qs = (
      qr(goliath._LTRACKPIN),
      qr(goliath._RTRACKPIN)
    )

    #Initialize the PS4 controller.
    self._controller = gamepad(goliath._MACADDRESS, self._buttonaction)

    self._waist = base(goliath._WAISTPIN)

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
    return v if abs(v) >= goliath._DZ else 0.0

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
#    print('riser:', dir)

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
        delta = max(0.01, nexttime - prevtime)
        prevtime = nexttime
        if delta > _dtime:
          delta = _dtime

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
    GPIO.cleanup()
