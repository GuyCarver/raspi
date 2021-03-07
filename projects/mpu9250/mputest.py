#!/usr/bin/env python3

#test code to read data from the mpu9250 and filter it with the mwick algorythm and
# output the yaw/pitch/roll values.

import mpu
import mwick
from time import sleep, perf_counter

mpu.startup()
ln = '-' * 30

atr = mpu.getacceltemprot()
m = mpu.getmag()

count = 0

gx = atr[0]
gy = atr[1]
gz = atr[2]
ax = atr[4]
ay = atr[5]
az = atr[6]
mx = m[0]
my = m[1]
mz = m[2]

ypr = mwick.updateypr(gx, gy, gz, ax, ay, az, mx, my, mz, 0.1)

ayaw = ypr[0]
apitch = ypr[1]
aroll = ypr[2]

prevtime = perf_counter()
while 1:
    atr = mpu.getacceltemprot()
#     print('ar:', atr[0], atr[1], atr[2], atr[4], atr[5], atr[6])
    m = mpu.getmag()

    gx = atr[0]
    gy = atr[1]
    gz = atr[2]
    ax = atr[4]
    ay = atr[5]
    az = atr[6]
    mx = m[0]
    my = m[1]
    mz = m[2]

    nexttime = perf_counter()
    dt = max(0.01, nexttime - prevtime)
    prevtime = nexttime
    ypr = mwick.updateypr(gx, gy, gz, ax, ay, az, mx, my, mz, dt)

    ayaw = (ayaw + ypr[0]) / 2.0
    apitch = (apitch + ypr[1]) / 2.0
    aroll = (aroll + ypr[2]) / 2.0

    print('cur: {:10.4f}, {:10.4f}, {:10.4f}                    '.format(ypr[0], ypr[1], ypr[2]), end='\r')

    count += 1

    if count == 20:
      count = 0
      print('ave: {:10.4f}, {:10.4f}, {:10.4f}                    '.format(ayaw, apitch, aroll))
    else:
      sleep(0.25)
