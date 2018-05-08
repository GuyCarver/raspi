
from kivy.base import EventLoop
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from functools import partial
from time import sleep

class Listener(object):

  def on_motion(self, etype, me):
    print("Receive event of type {}: {}".format(etype, me))

  def on_start(self):
    print('starting')
    sound = SoundLoader.load('sounds/startup.mp3') #insert a sound here
    sound.bind(on_stop=self.stop_event)
    Clock.schedule_once(partial(self.play_sound, sound))
    Clock.schedule_once(partial(self.play_sound, sound), 10.0)

  def play_sound(self, sound, dt):
    print('playing')
    sound.play()

  def stop_event(self, sound):
    print(sound, 'stopping')

if __name__ == '__main__':
  myl = Listener()
  EventLoop.add_event_listener(myl)
  EventLoop.start()
  myl.on_start()
  while 1:
    EventLoop.idle()
    sleep(0.016)
