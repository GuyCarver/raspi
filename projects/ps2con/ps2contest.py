from ps2con import *
from time import sleep

class dude(object):
  '''docstring for dude'''
  def __init__( self ):
    self._btn = 3

  def mycallback( self, aButton, aValue ):
    if aValue & 0x02:
      print(aButton, aValue)

def test(  ):
  ''' '''
  d = dude()
  p = ps2con(27, 22, 18, 17, d.mycallback)
  while 1:
    p.update()
    print(p, end='\r')
#    for i, v in enumerate(p):
#      print(hex(v), ',', end='')
#    print(';', end='\r')

    sleep(0.1)

test()