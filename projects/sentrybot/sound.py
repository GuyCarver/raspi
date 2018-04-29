#!/usr/bin/env python3

#sound playback using kivy.

from kivy.core import audio

#NOTE: In order for sounds to play correctly we have to use an EventLoop
# with a Listener.  The listener needn't do anything and the EventLoop.idle()
# function must be called regularly.  This will enable sounds to loop as
# well as to report events such as on_stop.

class sound(object):
  '''docstring for sound'''
  _DIR = 'sounds/'

  @classmethod
  def on_start( self ):
    '''Empty even handler function.  This is here because we use
       the sound class as the EventLoop event listener'''
    print('starting listener')

  def __init__( self, aFile, aCallback = None ):
    self._callback = aCallback
    self._sound = audio.SoundLoader.load(sound._DIR + aFile)
    self._sound.load()
    self._sound.on_stop = self.stopping

  @property
  def callback( self ):
    return self._callback

  @callback.setter
  def callback( self, aCallback ):
    self._callback = aCallback

  @property
  def playing( self ):
    return self._sound.get_pos() < self._sound.length

  @property
  def loop( self ):
    return self._sound.loop

  @property
  def source( self ):
    return self._sound.source

  @loop.setter
  def loop( self, aValue ):
    self._sound.loop = aValue

  def play( self ):
    '''  '''
    self._sound.play()

  def stop( self ):
    '''  '''
    self._sound.stop()

  def stopping( self ):
    '''  '''
    if self._callback:
      self._callback(self)

from kivy.base import EventLoop
from time import sleep

if __name__ == '__main__':
  def MyStop( aSound ):
    ''' '''
    print('Stopping', aSound.source)

  EventLoop.add_event_listener(sound)
  s = sound('startup.mp3', MyStop)
  EventLoop.start()
  s.play()
  while 1:
    EventLoop.idle()
    sleep(0.016)
