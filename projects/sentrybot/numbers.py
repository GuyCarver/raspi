#!/usr/bin/env python3

#Module to say numbers.

from sound import sound, soundchain

_SOUNDFILES  = ('numbers\\plus', None, 'numbers\\minus', 'sys\\point', 'None', 'numbers\\zero',
                'sys\\one', 'sys\\two', 'sys\\three', 'sys\\four',
                'sys\\five', 'numbers\\six', 'numbers\\seven', 'numbers\\eight', 'numbers\\nine')

def makesoundchain( aNumber, aPrefix = None, aPostfix = None ):
  snds = []

  if aPrefix:
    snds.append(aPrefix)

  numberstr = str(aNumber)

  for c in numberstr:
    d = ord(c) - 0x2B #ord('0') = 0x30
    if d >= 0 and d < len(_SOUNDFILES) and _SOUNDFILES[d] != None:
      snds.append(_SOUNDFILES[d])
    else:
      return None

  if aPostfix:
    snds.append(aPostfix)

  return soundchain(snds, 1)


if __name__ == '__main__':
  from time import sleep
  from kivy.base import EventLoop

  running = True
  sound.start()

  s1 = makesoundchain(25, aPrefix = 'sys\\movement', aPostfix = 'sys\\percent')
  if s1:
    def cb(x):
      global running
      running = False
    s1.callback = cb
    s1.play()

    while running:
      EventLoop.idle()
      sleep(0.033)
