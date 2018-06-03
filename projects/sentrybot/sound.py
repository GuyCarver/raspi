#!/usr/bin/env python3

#sound playback using kivy.

from kivy.core import audio
from kivy.base import EventLoop

#NOTE: In order for sounds to play correctly we have to use an EventLoop
# with a Listener.  The listener needn't do anything and the EventLoop.idle()
# function must be called regularly.  This will enable sounds to loop as
# well as to report events such as on_stop.

#------------------------------------------------------------------------
class sound(object):
  '''Use kivy to play sounds.  Sounds are also grouped so only certain ones may play at a time.'''
  _DIR = 'sounds/'

  _playinggroups = {  }
  _defaultcallback = None

  @classmethod
  def setdefaultcallback( self, aCallback ):
    self._defaultcallback = aCallback

  @classmethod
  def start( self ):
    '''Start the event loop listener for sound events.  We only care about on_stop.'''
    EventLoop.add_event_listener(self)
    EventLoop.start()

  @classmethod
  def on_start( self ):
    '''Empty even handler function.  This is here because we use
       the sound class as the EventLoop event listener'''
    pass
#    print('starting listener')

  def __init__( self, aFile, aGroup = 0, aCallback = None ):
    self._filename = aFile                      #Keep track of base file name.
    self._group = aGroup                        #Only 1 sound in a group may play at a time.
    self._keeploaded = False                    #When True sound will never be unloaded.
    self._loaded = False                        #When True the sound data is loaded.
    self._loop = False                          #Keep a local looping state.
    self._volume = 1                            #Keep a local volume level.
    self._next = None                           #Next sound to play in chain if any.

    #Make sure group exists in the dict.
    if not aGroup in sound._playinggroups:
      sound._playinggroups[aGroup] = None

    fname = sound._DIR + aFile + '.mp3'
    #Create the sound object. This does not actually load the sound data.
    self._sound = audio.SoundLoader.load(fname)

    self._callback = aCallback                  #Sound stop callback function.
    self._sound.on_stop = self.stopping

  @property
  def next( self ):
    return self._next

  @next.setter
  def next( self, aValue ):
    self._next = aValue

  @property
  def keeploaded( self ):
    return self._keeploaded

  @keeploaded.setter
  def keeploaded( self, aValue ):
    self._keeploaded = aValue

  @property
  def group( self ): return self._group

  @property
  def volume( self ):
    return self._volume

  @volume.setter
  def volume( self, aValue ):
    self._volume = aValue
    if self.playing:
      self._sound.volume = aValue

  @property
  def loaded( self ): return self._loaded

  @property
  def filename( self ): return self._filename

  @property
  def source( self ): return self._sound.source if self.loaded else ''

  @property
  def callback( self ):
    return self._callback

  @callback.setter
  def callback( self, aCallback ):
    self._callback = aCallback

  @property
  def playing( self ):
    return self.loaded and (self._sound.get_pos() < self._sound.length)

  @property
  def loop( self ):
    return self._loop

  @loop.setter
  def loop( self, aValue ):
    self._loop = aValue
    if self.loaded:
      self._sound.loop = aValue

  def load( self ):
    '''load the sound.  This is necessary before it can play and is called by play(), but the sound
       may also be pre-loaded.'''
    if not self.loaded:
      self._sound.load()
      self._loaded = True

  def unload( self, force ):
    '''Unload sound data. if force = False then wont unload if keeploaded set.'''
    if self.loaded:
      if force or not self.keeploaded:
        self._sound.unload()
        self._loaded = False

  def play( self ):
    '''Play the sound.  Stops any other sound in this sounds group before playback.  If this
       sound was already playing, it will re-start.'''
    sound.stopgroup(self)                       #Make sure any other sound in this group is stopped.
    sound._playinggroups[self.group] = self
    self.load()                                 #Make sure the sound is loaded.
    #NOTE: May need to rewind the sound here.
    self._sound.loop = self._loop
    self._sound.volume = self._volume
    self._sound.play()

  def stop( self ):
    '''Stop sound from playing if it is currently playing.'''
    if self.playing:
      self._sound.stop()
#      self.unload(False)                       #Unload the sound only if it's not flagged for keep.

  @classmethod
  def stopgroup( self, aSound ):
    '''Stop current sound for the group aSound belongs to.
       This is done in preparation for aSound to play.'''
    g = aSound.group
#    print('group', g)
    s = self._playinggroups[g]

    #Don't stop sound if it's the given sound because we are going to just
    # play it again soon.
    if s != None and s != aSound:
#      print('interrupt:', s.source)
      s.stop()                                  #Stop sound.
      self._playinggroups[g] = None             #Clear now rather than wait for stop event.

  def stopping( self ):
    '''Callback function called by the Kivy event system when a sound stops playing.'''

    #If this sound is set as the group sound, then clear it.
    if sound._playinggroups[self.group] == self:
      sound._playinggroups[self.group] = None

    #If callback function supplied, then call it.
    if self._callback:
      self._callback(self)

    if self.next:
      self.next.play()

    self.unload(False)                            #Unload unless keeploaded set.

#------------------------------------------------------------------------
class soundchain(object):
  '''Play a list of sounds one after the other.'''

  def __init__( self, aFiles, aGroup ):
    self._files = aFiles
    self._index = 0
    self._group = aGroup
    self._sound = None

  def play( self ):
    '''  '''
    self._sound = sound(self._files[self._index], self._group, self._sounddone)
    self._sound.play()

  def reset( self, aArg ):
    '''  '''
    self._index = 0
    self._sound = None

  def _sounddone( self, aSound ):
    '''Callback function to play next sound.'''
    self._index += 1
    if self._index < len(self._files):
      self.play()
    else:
      self._index = 0
      self._sound = None

#------------------------------------------------------------------------
if __name__ == '__main__':
  from time import sleep
  from kivy.clock import Clock
  running = True

  def MyStop( aSound ):
    '''  '''
    print('Stopping', aSound.source)
#    running = False

  #start Kivy sound event system.
  sound.start()

  s2 = soundchain(('sys\\startup', 'sys\\five', 'sys\\four', 'sys\\three', 'sys\\two', 'sys\\one'), 0)
  s = sound('startup', 1, MyStop)
  s.play()
  def startsound( dt ):
    s2.play()

  Clock.schedule_once(startsound, 2.0)

  while running:
    EventLoop.idle()
    sleep(0.033)
