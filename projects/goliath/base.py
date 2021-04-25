#!/usr/bin/env python3
#Run the waist motor using an mcp4725 and a direction pin.

import RPi.GPIO as gp
from mcp4725 import *

class base(object):
  ''' Object to handle the motor controller controlling the base rotation motor. '''

  def __init__( self, aRevPin ):
    ''' reverse button # '''
    gp.setup(aRevPin, gp.OUT)

    #Make sure gpio is initialized.
    if gp.getmode() != gp.BCM:
      gp.setwarnings(False)
      gp.setmode(gp.BCM)

    self._mcp = mcp()
    self._speed = 0.0
    self._reverse = False
    self._revpin = aRevPin
    self.reverse = False

  @property
  def reverse( self ):
    return self._reverse

  @reverse.setter
  def reverse( self, aValue ):
    self._reverse = aValue
    gp.output(self._revpin, aValue)

  @property
  def speed( self ):
    return self._speed

  @speed.setter
  def speed( self, aValue ):
    ''' Set speed to value from -1.0 to 1.0. '''
    self._speed = aValue
    self.reverse = self._speed >= 0.0
    v = int(abs(aValue) * 4095.0)
    self._mcp.set(v)

