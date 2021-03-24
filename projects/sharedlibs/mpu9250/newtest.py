#!/usr/bin/env python3

from time import perf_counter, sleep
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250
import mwick

ln = '-' * 30

mwick.setsamplefreq(512.0)

mpu = MPU9250(
    address_ak=AK8963_ADDRESS,
    address_mpu_master=MPU9050_ADDRESS_68, # In 0x68 Address
    address_mpu_slave=None,
    bus=1,
    gfs=GFS_1000,
    afs=AFS_8G,
    mfs=AK8963_BIT_16,
    mode=AK8963_MODE_C100HZ)

mpu.calibrate()
mpu.configure() # Apply the settings to the registers.

acc = mpu.readAccelerometerMaster()
gyr = mpu.readGyroscopeMaster()
mag = mpu.readMagnetometerMaster()

ypr = mwick.updateypr(gyr[0], gyr[1], gyr[2],
  acc[0], acc[1], acc[2], mag[0], mag[1], mag[2], 0.1)

ayaw = ypr[0]
apitch = ypr[1]
aroll = ypr[2]

count = 0
prevtime = perf_counter()

while True:
  gyr = mpu.readGyroscopeMaster()
  mag = mpu.readMagnetometerMaster()
  acc = mpu.readAccelerometerMaster()

  nexttime = perf_counter()
  dt = max(0.01, nexttime - prevtime)
  prevtime = nexttime
  ypr = mwick.updateypr(gyr[0], gyr[1], gyr[2],
    acc[0], acc[1], acc[2], mag[0], mag[1], mag[2], dt)

  ayaw = (ayaw + ypr[0]) / 2.0
  apitch = (apitch + ypr[1]) / 2.0
  aroll = (aroll + ypr[2]) / 2.0

  print('cur:', ypr[0], ypr[1], ypr[2], '                  ', end='\r')

#   print('{:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}             '.format(
#     acc[0], acc[1], acc[2], gyr[0], gyr[1], gyr[2], mag[0], mag[1], mag[2]), end='\r')
  count += 1

  if count == 20:
    count = 0
    print('ave:', ayaw, apitch, aroll, ' ' * 20)
  else:
    sleep(0.25)
