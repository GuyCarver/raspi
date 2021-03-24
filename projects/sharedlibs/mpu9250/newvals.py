#!/usr/bin/env python3

#Test code to output mpu9250 raw accelerometer/gyro and magneto values to console.

import time
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

mpu = MPU9250(
    address_ak=AK8963_ADDRESS,
    address_mpu_master=MPU9050_ADDRESS_68, # In 0x68 Address
    address_mpu_slave=None,
    bus=1,
    gfs=GFS_1000,
    afs=AFS_8G,
    mfs=AK8963_BIT_16,
    mode=AK8963_MODE_C100HZ)

# mpu.calibrate()
mpu.configure() # Apply the settings to the registers.

while 1:
  acc = mpu.readAccelerometerMaster()
  gyr = mpu.readGyroscopeMaster()
  mag = mpu.readMagnetometerMaster()

  print('{:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}, {:10.4f}'.format(
    acc[0], acc[1], acc[2], gyr[0], gyr[1], gyr[2], mag[0], mag[1], mag[2]), end='\r')
  time.sleep(0.25)
