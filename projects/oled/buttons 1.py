#!/usr/bin/env python3
#handle button input.

import RPi.GPIO as GPIO
#import time

class button(object):
  """Handle input from a single button channel on GPIO."""
  
  NOACTION = 0
  PRESSED = 1
  RELEASED = 2
  
  def __init__( self, channel ) :
    super(button, self).__init__()
    self._channel = channel
    GPIO.setup(channel, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    self._curstate = 1  #start out high (not pressed).
    self._prevstate = 1

  @property
  def state( self ) :
    return self._curstate

  @property
  def pressed( self ) :
    '''return 1 if pressed else 0'''
    return (self._prevstate ^ self._curstate) & self._prevstate

  @property
  def released( self ) :
    '''return 1 if released else 0'''
    return (self._prevstate ^ self._curstate) & self._curstate

  def update( self ) :
    self._prevstate = self._curstate
    self._curstate = GPIO.input(self._channel)
    res = button.NOACTION
    if self._curstate != self._prevstate :
      res = button.RELEASED if self._curstate else button.PRESSED
    return res

#def test(  ):
#  GPIO.setwarnings(False)
#  GPIO.setmode(GPIO.BCM)
#  b = button(11)
#  running = True;
#  try:
#    while running :
#      b.update()
##      if b._curstate != b._prevstate :
##        print("p:{} c:{}".format(b._prevstate, b._curstate))
#      p = b.pressed
#      if p :
#        print("pressed")
#      r = b.released
#      if r :
#        print("released")
#      time.sleep(0.2)
#  except KeyboardInterrupt:
#    print("exiting.")
#    running = False
#
#if __name__ == '__main__':  #start server and open browser
#  test()
#  print('done')

