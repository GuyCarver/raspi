#!/usr/bin/python3

import smbus
import math
from time import sleep

power_mgmt_1 = 0x6b
power_mgmt_2 = 0x6c

def read_byte(reg):
    return bus.read_byte_data(address, reg)

def read_word(reg):
    h = bus.read_byte_data(address, reg)
    l = bus.read_byte_data(address, reg+1)
    value = (h << 8) + l
    return value

def read_word_2c(reg):
  try:
    val = read_word(reg)
    if (val >= 0x8000):
        val = -((65535 - val) + 1)
  except:
    val = 0

  return val

def dist(a,b):
    return math.sqrt((a*a)+(b*b))

def get_y_rotation(x,y,z):
    radians = math.atan2(x, dist(y,z))
    return -math.degrees(radians)

def get_x_rotation(x,y,z):
    radians = math.atan2(y, dist(x,z))
    return math.degrees(radians)

bus = smbus.SMBus(1)
address = 0x68

bus.write_byte_data(address, power_mgmt_1, 0)

if __name__ == '__main__':
  while(True):
    rot_x = read_word_2c(0x43) / 131.0
    rot_y = read_word_2c(0x45) / 131.0
    rot_z = read_word_2c(0x47) / 131.0

    accel_x = read_word_2c(0x3b) / 16384.0
    accel_y = read_word_2c(0x3d) / 16384.0
    accel_z = read_word_2c(0x3f) / 16384.0
    print(accel_x, accel_y, accel_z, rot_x, rot_y, rot_z)
#     print(rot_x, rot_y, rot_z)
#     print(get_x_rotation(rot_x, rot_y, rot_z), get_y_rotation(rot_x, rot_y, rot_z), end='\r')
    sleep(0.1)
