#!/usr/bin/env python3
#handle button input.

import RPi.GPIO as GPIO

def gpioinit(  ):
  GPIO.setwarnings(False)
  GPIO.setmode(GPIO.BCM)

class button(object):
  """Handle input from a single button channel on GPIO."""

  DOWN = 0        #Indicates button is currently being pressed.
  UP = 1          #Indicates the button is not pressed.
  STATE = 1       #Mask for button state.
  CHANGE = 2      #Indicates button has changed state since last update.

  @staticmethod
  def justpressed( aState ) :
    return aState == button.CHANGE | button.DOWN

  @staticmethod
  def ison( aState ):
    '''return True if given button state is on'''
    return (aState & button.STATE) == button.DOWN

  @staticmethod
  def ischanged( aState ):
    '''return True if given button state indicates it changed.'''
    return (aState & button.CHANGE) != 0

  def __init__( self, channel ):
    super(button, self).__init__()
    self._channel = channel
    GPIO.setup(channel, GPIO.IN, pull_up_down = GPIO.PUD_UP)
    self._curstate = 1  #start out high (not pressed).
    self._prevstate = 1

  @property
  def channel( self ):
    return self._channel

  @property
  def state( self ):
    return self._curstate

  @property
  def pressed( self ):
    '''return 1 if button just pressed else 0'''
    return (self._prevstate ^ self._curstate) & self._prevstate & button.STATE

  @property
  def released( self ):
    '''return 1 if button just released else 0'''
    return (self._prevstate ^ self._curstate) & self._curstate & button.STATE

  @property
  def on( self ):
    '''return True if button state is on'''
    return button.ison(self._curstate)

  def update( self ):
    '''Update button state and returns state + change flag.'''
    self._prevstate = self._curstate
    res = GPIO.input(self._channel)
    if res != (self._prevstate & button.STATE):
      res |= button.CHANGE

    self._curstate = res

    return res

if __name__ == '__main__':  #start server and open browser
  import time

  #Snooze, Alarm On/Off Switch, Alarm Set, Minute, Hour, Time Set (Update temp)
  ButtonIDS = [12, 5, 6, 13, 19, 26]

  def test(  ):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    MyButtons = [ button(x) for x in ButtonIDS ]

    running = True;
    try:
      while running:
        for b in MyButtons:
          state = b.update()
          if state & button.CHANGE:
            print("{} is {}".format(b.channel, "released" if state & button.UP else "pressed"))
        time.sleep(0.2)
    except KeyboardInterrupt:
      print("exiting.")
      running = False

  test()
  print('done')

