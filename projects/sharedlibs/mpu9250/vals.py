#!/usr/bin/env python3

#Test code to output mpu9250 raw accelerometer/gyro and magneto values to console.

import mpu9250
import time
# import oled

mpu9250.startup()
# oled.startup()
# oled.setdim(0xFF)

while 1:
  rta = mpu9250.getrottempaccel()
  m = mpu9250.getmag()

  def formattxt( aItem, aVal ):
    return '{}:{:3.2f}'.format(aItem, aVal)

#   y = 0
#   oled.text((0, y), formattxt('x', m[0]))
#   y = h
#   oled.text((0, y), formattxt('y', m[1]))
#   y += h
#   oled.text((0, y), formattxt('z', m[2]))
#   oled.display()
  print('{:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}'.format(
    rta[0], rta[1], rta[2], rta[4], rta[5], rta[6], m[0], m[1], m[2]), end='\r')
  time.sleep(0.25)
