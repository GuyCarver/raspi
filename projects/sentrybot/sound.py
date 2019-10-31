#!/usr/bin/env python3
#11/10/2018 11:10 AM

#sound playback using kivy.

from pygame import mixer
from kivy.base import EventLoop
from bt import *

#NOTE: In order for sounds to play correctly we have to use an EventLoop
# with a Listener.  The listener needn't do anything and the EventLoop.idle()
# function must be called regularly.  This will enable sounds to loop as
# well as to report events such as on_stop.

#------------------------------------------------------------------------
class sound(object):
  '''Use kivy to play sounds.  Sounds are also grouped so only certain ones may play at a time.'''
  _DIR = 'sounds/'

  _playinggroups = {  }

  @classmethod
  def start( self ):
    '''Initialize the pygame mixer. Start the event loop listener for sound events.  We only care about on_stop.'''
    EventLoop.add_event_listener(self)
    EventLoop.start()
    mixer.init(buffer = 512)
    mixer.set_num_channels(5)

  @classmethod
  def on_start( self ):
    '''Empty event handler function.  This is here because we use
       the sound class as the EventLoop event listener'''
    pass
#    print('starting listener')

  def __init__( self, aFile, aGroup = 0 ):
    self._filename = aFile                      #Keep track of base file name.
    self._group = mixer.Channel(aGroup)         #Only 1 sound in a group may play at a time.
    self.loop = False                           #Keep a local looping state.

    fname = sound._DIR + aFile + '.ogg'
    #Create the sound object. This does not actually load the sound data.
    self._sound = mixer.Sound(fname)

  @property
  def group( self ): return self._group

  @property
  def volume( self ):
    return self._sound.get_volume()

  @volume.setter
  def volume( self, aValue ):
    self._sound.set_volume(aValue)

  @property
  def filename( self ): return self._filename

  @property
  def source( self ): return self._sound.source if self.loaded else ''

  @property
  def playing( self ):
    return self._group.get_sound() == self._sound()

  @property
  def loop( self ):
    return self._loop

  @loop.setter
  def loop( self, aValue ):
    self._loop = -1 if aValue else 0

  def play( self ):
    '''Play the sound.  Stops any other sound in this sounds group before playback.  If this
       sound was already playing, it will re-start.'''
    self._group.play(self._sound, loops = self._loop)

  def stop( self ):
    '''Stop sound from playing if it is currently playing.'''
    self._sound.stop()

  @classmethod
  def stopgroup( self, aSound ):
    '''Stop current sound for the group aSound belongs to.
       This is done in preparation for aSound to play.'''
    aSound.group.stop()
#    print('group', g)

#------------------------------------------------------------------------
class soundchain(object):
  '''Play a list of sounds one after the other.'''

  _chains = []

  def __init__( self, aFiles, aGroup ):
    self._files = aFiles
    self._index = 0
    self._group = mixer.Channel(aGroup)
    self._sound = None
    soundchain._chains.append(self)

  def __del__( self ):
    soundchain._chains.remove(self)

  @classmethod
  def pump( self ):
    for s in self._chains:
      s.update()

  @property
  def playing( self ):
    return  self._group.get_busy()

  def _play( self ):
    '''  '''
    fname = sound._DIR + self._files[self._index] + '.ogg'
    print('playing', fname)
    self._sound = mixer.Sound(fname)
    self._group.play(self._sound)

  def play( self ):
    '''  '''
    self._index = 0
    if len(self._files):
      self._play()

  def update( self ):
    print('updating')
    if self._sound != None:
      if not self._group.get_busy():
        print('sound done')
        self._index += 1
        if self._index < len(self._files):
          self._play()
        else:
          self.reset()

  def add( self, aSound ):
    '''Add sound to end of list.'''
    self._files.append(aSound)

  def prepend( self, aSound ):
    '''Add sound to beginning of list.'''
    self._files.insert(0, aSound)

  def reset( self ):
    '''  '''
    self._index = 0
    self._sound = None

#------------------------------------------------------------------------
if __name__ == '__main__':
  from time import sleep
  import os

#  Device A0:E9:DB:10:37:09 Inateck BP1001
#  id = 'A0:E9:DB:10:37:09'
#  bl = Bluetoothctl()
#  res = bl.connect(id)
#  if res != True:
#    print("BT connect failed!")

  sound.start()

  s2 = soundchain(('sys/startup', 'sys/five', 'sys/four', 'sys/three', 'sys/two', 'sys/one'), 0)
  s = sound('startup', 1)
  s3 = sound('sys/green', 2)
  s4 = sound('sys/percent', 3)
  s5 = sound('sys/point', 4)
  s.play()
  s2.play()
  s3.play()
  s4.play()
  s5.play()

  Running = True

  while Running:
    s2.update()
#    soundchain.pump()
    sleep(0.033)
    Running = s2.playing
