#!/usr/bin/env python3

from time import sleep
import ps2con

def mycallback( aBtn, aValue ):
  print(ps2con.GetName(aBtn), "=", aValue)

def test(  ):
  ''' '''
  ps2con.Startup(17, 27, 18, 4)
  while 1:
    ps2con.Update(mycallback)
    sleep(0.1)

test()