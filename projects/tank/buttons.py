#!/usr/bin/env python3
#handle button input.

# sudo apt install rpi.gpio

import RPi.GPIO as gp
# gp.output(sentrybot._SMOKEPIN, gp.HIGH if abTF else gp.LOW)
# gp.setup(sentrybot._SMOKEPIN, gp.OUT)
# gp.setup(channel, gp.IN, pull_up_down = gp.PUD_UP)
# res = gp.input(self._channel)

class button(object):
  ''' Handle input from a single button channel on gp. '''

  def __init__( self, channel ):
    super(button, self).__init__()

    #Make sure gpio is initialized.
    if gp.getmode() != gp.BCM:
      gp.setwarnings(False)
      gp.setmode(gp.BCM)

    self._channel = channel
    gp.setup(channel, gp.IN, pull_up_down = gp.PUD_UP)
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
    res = gp.input(self._channel)
    self._curstate = (res == 0)                 # 0 = button pressed.

if __name__ == '__main__':
  import sys
  from time import sleep
  bi = 4
  if len(sys.argv) > 1:
    bi = int(sys.argv[1])

  b = button(bi)
  while True:
    b.update()
    print('State: ', b.state, '     ', end='\r')
    sleep(0.1)

