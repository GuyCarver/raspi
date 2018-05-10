#!/usr/bin/env python3

#sound playback using kivy.

from kivy.core import audio
from kivy.base import EventLoop

#NOTE: In order for sounds to play correctly we have to use an EventLoop
# with a Listener.  The listener needn't do anything and the EventLoop.idle()
# function must be called regularly.  This will enable sounds to loop as
# well as to report events such as on_stop.

class sound(object):
  '''docstring for sound'''
  _DIR = 'sounds/'

  _playinggroups = {  }

  @classmethod
  def start( self ):
    '''Start the event loop listener for sound events.  We only care about on_stop.'''
    EventLoop.add_event_listener(self)
    EventLoop.start()

  @staticmethod
  def update(  ):
    '''Called once per frame to pump the sound event listener.'''
    EventLoop.idle()

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
    self._loaded = False;                       #When True the sound data is loaded.

    #Make sure group exists in the dict.
    if not aGroup in sound._playinggroups:
      sound._playinggroups[aGroup] = None

    #Create the sound object. This does not actually load the sound data.
    self._sound = audio.SoundLoader.load(sound._DIR + aFile)

    self._callback = aCallback                  #Sound stop callback function.
    #If sound stop callback given, set it.
    if aCallback != None:
      self._sound.on_stop = self.stopping

  @property
  def keeploaded( self ):
    return self._keeploaded

  @keeploaded.setter
  def keeploaded( self, aValue ):
    self._keeploaded = aValue

  @property
  def group( self ): return self._group

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
    return self._sound.loop if self.loaded else False

  @loop.setter
  def loop( self, aValue ):
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

    self.unload(False)                            #Unload unless keeploaded set.


if __name__ == '__main__':
  from time import sleep
  running = True

  def MyStop( aSound ):
    ''' '''
#    print('Stopping', aSound.source)
    running = False

  #start Kivy sound event system.
  sound.start()

  s = sound('startup.mp3', 0, MyStop)
  s.play()
  cnt = 0

  while running:
    EventLoop.idle()
    cnt += 1
    if cnt > 70:
      s.stop()
      break
    sleep(0.033)
