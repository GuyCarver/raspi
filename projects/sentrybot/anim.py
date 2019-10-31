#!/usr/bin/env python3
#11/10/2018 11:10 AM

from kivy.base import EventLoop
from kivy.animation import Animation
from time import sleep

class AnimRecorder(object):
  '''docstring for AnimRecorder'''
  def __init__( self ):
    #todo: Create buffer for animation data.
    pass

  def _buttonaction( self, aButton, aValue ):
    #todo: record button action.
    pass

  def _joyaction( self, aJoy, aValue ):
    #todo: record joystick action.
    pass

class MyAnim(object):
  '''docstring for MyAnim'''
  def __init__( self, aValue ):
    super(MyAnim, self).__init__()
    self._value = aValue
    self.uid = 0
    self.run = True

  @property
  def value( self ):
    return self._value

  @value.setter
  def value( self, aValue ):
    self._value = aValue

  def done( self, aAnim, aWidget ):
    '''  '''
    self.run = False

class buttonanim(object):
  '''docstring for buttonanim'''
  def __init__( self, aButton ):
    super(buttonanim, self).__init__()
    self._button = aButton
    self._value = 0.0

  @property
  def value( self ):
    return self._value

  @value.setter
  def value( self, aValue ):
    aValue = min(max(0.0, aValue), 1.0)
    if self._value != aValue:
      self._value = aValue
      if self._value == 0.0:
        #todo: send button up event.
      elif self._value == 1.0:
        #todo: send button down event.

if __name__ == '__main__':
  m = MyAnim(10.0)
  EventLoop.add_event_listener(m)
  EventLoop.start()
  a = Animation(value=20.0, duration=2.0)
  a += Animation(value=15.0, duration=1.0)
  a.bind(on_complete=m.done)
  a.start(m)

  while m.run:
    EventLoop.idle()
    print(m.value)
    sleep(0.1)


#Part Name
#value, time, transition
#All values are absolute, but we want to use deltas, so we need to figure out how
# to indicate when a value is absolute and when it is a delta. Prepend 'a-' to the transition name

#Audio
#File name
