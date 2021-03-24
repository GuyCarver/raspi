#!/usr/bin/env python3

from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250
import mwick

#todo: Calc/Save/Load calibration data.

#--------------------------------------------------------
class orient(object):
  '''  '''

  #--------------------------------------------------------
  def __init__( self ):
    '''  '''
    self._mpu = MPU9250(
        address_ak=AK8963_ADDRESS,
        address_mpu_master=MPU9050_ADDRESS_68, # In 0x68 Address
        address_mpu_slave=None,
        bus=1,
        gfs=GFS_1000,
        afs=AFS_8G,
        mfs=AK8963_BIT_16,
        mode=AK8963_MODE_C100HZ)

    # self._mpu.calibrate()
    self._mpu.configure() # Apply the settings to the registers.

    a = self._mpu.readAccelerometerMaster()
    g = self._mpu.readGyroscopeMaster()
    m = self._mpu.readMagnetometerMaster()

    self._ypr = mwick.updateypr(g[0], g[1], g[2], a[0], a[1], a[2], m[0], m[1], m[2], 0.1)

    self._prevtime = perf_counter()

    self._minext = 0.0
    self._maxext = 0.0

  #--------------------------------------------------------
  def update( self ):
    '''  '''

    a = self._mpu.readAccelerometerMaster()
    g = self._mpu.readGyroscopeMaster()
    m = self._mpu.readMagnetometerMaster()

    #Calculate the delta time in seconds since the last update.
    nexttime = perf_counter()
    dt = max(0.01, nexttime - self._prevtime)
    self._prevtime = nexttime

    self._ypr = mwick.updateypr(g[0], g[1], g[2], a[0], a[1], a[2], m[0], m[1], m[2], dt)

  #--------------------------------------------------------
  @property
  def x( self ): return self._ypr[0]

  #--------------------------------------------------------
  @property
  def y( self ): return self._ypr[1]

  #--------------------------------------------------------
  @property
  def z( self ): return self._ypr[2]

  #--------------------------------------------------------
  def UpdateExtents( self ):
    self.update()
    x = self.x
    self._minext = min(self._minext, x)
    self._maxext = max(self._maxext, x)
