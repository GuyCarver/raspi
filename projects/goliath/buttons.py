#!/usr/bin/env python3
#handle button input.

# sudo apt install rpi.gpio

import RPi.GPIO as GPIO
# GPIO.output(sentrybot._SMOKEPIN, GPIO.HIGH if abTF else GPIO.LOW)
# GPIO.setup(sentrybot._SMOKEPIN, GPIO.OUT)
# GPIO.setup(channel, GPIO.IN, pull_up_down = GPIO.PUD_UP)
# res = GPIO.input(self._channel)

def gpioinit(  ):
  GPIO.setwarnings(False)
  GPIO.setmode(GPIO.BCM)

class button(object):
  ''' Handle input from a single button channel on GPIO. '''

  def __init__( self, channel ):
    super(button, self).__init__()
    self._channel = channel
    GPIO.setup(channel, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    self._curstate = False
    self._prevstate = False

  @property
  def channel( self ):
    return self._channel

  @property
  def state( self ):
    return self._curstate

  @property
  def pressed( self ):
    ''' Return True if button just pressed. '''
    return (self._prevstate ^ self._curstate) & self._curstate

  @property
  def released( self ):
    ''' Return True if button just released. '''
    return (self._prevstate ^ self._curstate) & self._prevstate

  @property
  def on( self ):
    ''' Return True if button state is on. '''
    return self._curstate

  def update( self ):
    ''' Update button state and returns state + change flag. '''
    self._prevstate = self._curstate
    res = GPIO.input(self._channel)
    self._curstate = (res == 0)                 # 0 = button pressed.

