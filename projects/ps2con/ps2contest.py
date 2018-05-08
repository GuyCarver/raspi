from ps2con import *
import wiringpi

class dude(object):
  '''docstring for dude'''
  def __init__( self ):
    self._btn = 3

  def mycallback( self, aButton, aValue ):
    if aButton == self._btn:
      print(aButton, aValue)

def test(  ):
  ''' '''
  d = dude()
  p = ps2con(27, 22, 18, 17, d.mycallback)
  while 1:
    p.update()
    for i, v in enumerate(p):
      print(hex(v), ',', end='')
    print(';', end='\r')

    wiringpi.delayMicroseconds(1000)

test()