#!/usr/bin/env python3

#Test code to output mpu9250 raw accelerometer/gyro and magneto values to console.

import mpu
import time

mpu.startup()

while 1:
    atr = mpu.getacceltemprot()
    m = mpu.getmag()

    print('{:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}'.format(
           atr[0], atr[1], atr[2], atr[4], atr[5], atr[6], m[0], m[1], m[2]), end='\r')
    time.sleep(0.25)
