#!/usr/bin/env python3

#interface to the mwicklib module.

from ctypes import CDLL, POINTER, c_float

_lib = CDLL('./mwicklib.so')

_lib.SetSampleFreq.argtypes = [c_float]
_lib.UpdateYPR.argtypes = [c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float]
_lib.Update.restype = POINTER(c_float * 4)
_lib.UpdateYPR.restype = POINTER(c_float * 3)

def update( gx, gy, gz, ax, ay, az, mx, my, mz, dt ):
  return _lib.Update(gx, gy, gz, ax, ay, az, mx, my, mz, dt).contents

def updateypr( gx, gy, gz, ax, ay, az, mx, my, mz, dt ):
  return _lib.UpdateYPR(gx, gy, gz, ax, ay, az, mx, my, mz, dt).contents

def setsamplefreq( freq ):
  _lib.SetSampleFreq(freq)

# def ToEuler( x, y, z, w ):
#   """ Convert a quaternion into euler angles (roll, pitch, yaw)
#   roll is rotation around x in radians (counterclockwise)
#   pitch is rotation around y in radians (counterclockwise)
#   yaw is rotation around z in radians (counterclockwise) """
#
#   t0 = 2.0 * (w * x + y * z)
#   t1 = 1.0 - (2.0 * (x * x + y * y))
#   roll_x = math.atan2(t0, t1)
#
#   t2 = 2.0 * (w * y - z * x)
#   t2 = 1.0 if t2 > 1.0 else t2
#   t2 = -1.0 if t2 < -1.0 else t2
#   pitch_y = math.asin(t2)
#
#   t3 = 2.0 * (w * z + x * y)
#   t4 = 1.0 - (2.0 * (y * y + z * z))
#   yaw_z = math.atan2(t3, t4)
#
#   return roll_x, pitch_y, yaw_z # in radians
