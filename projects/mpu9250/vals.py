#!/usr/bin/env python3

#Test code to output mpu9250 raw accelerometer/gyro and magneto values to console.

import mpu
import time
from oled import *
from terminalfont import *

mpu.startup()
o = oled()
o.rotation = 0
o.dim = 0xFF
sc = 2
h = terminalfont['Height'] * sc

while 1:
  atr = mpu.getacceltemprot()
  m = mpu.getmag()

  def formattxt( aItem, aVal ):
    return '{}:{:3.2f}'.format(aItem, aVal)

  y = 0
  o.text((0, y), formattxt('x', m[0]), 1, terminalfont, sc)
  y = h
  o.text((0, y), formattxt('y', m[1]), 1, terminalfont, sc)
  y += h
  o.text((0, y), formattxt('z', m[2]), 1, terminalfont, sc)
  o.display()
  o.clear()
#   print('{:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}'.format(
#     atr[0], atr[1], atr[2], atr[4], atr[5], atr[6], m[0], m[1], m[2]), end='\r')
  time.sleep(0.25)
