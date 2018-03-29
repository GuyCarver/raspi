#handle button input from a joystick.

import time

class button(object) :
  """Handle input from a single button channel on GPIO."""

  DOWN = 0        #Indicates button is currently being pressed.
  UP = 1          #Indicates the button is not pressed.
  STATE = 1       #Mask for button state.
  CHANGE = 2      #Indicates button has changed state since last update.

  _joy = None

  @classmethod
  def setjoy( cls, aJoy ) :
    cls._joy = aJoy

  @staticmethod
  def ison( aState ) :
    '''return True if given button state is on'''
    return (aState & button.STATE) == button.DOWN

  @staticmethod
  def ischanged( aState ) :
    '''return True if given button state indicates it changed.'''
    return (aState & button.CHANGE) != 0

  def __init__( self, channel ) :
    super(button, self).__init__()
    self._channel = channel
    self._curstate = 1  #start out high (not pressed).
    self._prevstate = 1

  @property
  def channel( self ) :
    return self._channel

  @property
  def state( self ) :
    return self._curstate

  @property
  def pressed( self ) :
    '''return 1 if button just pressed else 0'''
    return (self._prevstate ^ self._curstate) & self._prevstate & button.STATE

  @property
  def released( self ) :
    '''return 1 if button just released else 0'''
    return (self._prevstate ^ self._curstate) & self._curstate & button.STATE

  @property
  def on( self ) :
    '''return True if button state is on'''
    return button.ison(self._curstate)

  def update( self ) :
    '''Update button state and returns state + change flag.'''
    self._prevstate = self._curstate
    if self._joy != None :
      res = 1 - self._joy.get_button(self._channel)
      if res != (self._prevstate & button.STATE):
        res |= button.CHANGE
    else :
      res = 0

    self._curstate = res

    return res

#  def update( self ) :
#    '''Update button state and returns state + change flag.'''
#    self._prevstate = self._curstate
#    if self._joy != None :
#      self._curstate = 1 - self._joy.get_button(self._channel)
#      res = self._curstate
#      if self._curstate != self._prevstate :
#        res |= button.CHANGE
#    else :
#      res = 0
#
#    return res
#
