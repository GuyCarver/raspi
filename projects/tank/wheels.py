#!/usr/bin/env python3

import RPi.GPIO as GPIO

#This module controls the wheels of the tank using an L298n HBridge motor driver.
# The enable pins are connected to the pca9865 to control PWM signals for speek.
# The forward/backward lines are connected directly to raspi GPIO pins

class wheel(object):
  '''docstring for wheel'''

  _MINSPEED = 5  #Set this to whatever speed will prevent buzzing with no movement.

  def __init__( self, pca, index, forward, backward, dir ):
    super(wheel, self).__init__()
    self._pca = pca
    self._index = index
    self._forward = forward
    self._backward = backward
    self._scale = 1.0 * dir #Direction is encoded into scale with a +/- value.
    GPIO.setup((forward, backward), GPIO.OUT)
    self.speed = 0.0

  @property
  def scale( self ):
    return abs(self._scale)

  @scale.setter
  def scale( self, aValue ):
    d = self.direction
    aValue = min(1.0, max(0.0, aValue))
    self._scale = aValue * d

  @property
  def direction( self ):
    return 1 if self._scale >= 0 else -1

  @direction.setter
  def direction( self, aValue ):
    self._scale = abs(self._scale) * aValue

  @property
  def speed( self ):
    return self._speed

  @speed.setter
  def speed( self, aValue ):
    self._speed = aValue
    self._write()

  def off( self ):
    '''Turn the servo off.'''
    self._pca.off(self._index)

  def _write( self ):
    ''' Write speed out to the devices. '''

    s = self._speed * self._scale

    if s < -wheel.MINSPEED:
      f = 0
      b = 1
      s = -s
    elif s > wheel.MINSPEED:
      f = 1
      b = 0
    else:
      s = f = b = 0

    #Set the direction on the L298N
    GPIO.output(self._forward, f)
    GPIO.output(self._backward, b)
    #Set the speed on the pca.
    self._pca.set(self._index, min(100, s))

  def brake( self ) :
    """ Brake the motor by sending power both directions. """
    GPIO.output(self._forward, 1)
    GPIO.output(self._backward, 1)

    self._pca.set(self._index, 100)
    sleep(0.2)                                    #Wait for break to occur.
    self.speed = 0






