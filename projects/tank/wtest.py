#!/usr/bin/env python3
#test wheel velocity with a3144lib.

#from buttons import *
import pca9865 as pca
import a3144
from wheel import *
# from buttons import *
from time import sleep, perf_counter

# gpioinit()

pca.startup()
w = wheel(pca, 8, 9, 10)  #left
# w = wheel(pca, 4, 6, 5) #right

direction = 0
a = a3144.create(27)  #left = 27, right = 22
length = 0

def check():
  global length
  data = a3144.data(a)
  if data[0]:
    length += direction * data[0]
    print('ln:', length, data[0], data[1]) #, '       ', end='\r')

def sgn( aSpeed ):
  if aSpeed == 0.0:
    return 0
  return 1 if aSpeed > 0 else -1

def runit( aSpeed, aTime ):
  global direction

  direction = sgn(aSpeed)
  w.speed(aSpeed)
  start = perf_counter()
  while True:
    check()
    d = perf_counter() - start
    if d >= aTime:
      break
    sleep(0.01)

d = 2.0

runit(0.025, d)
runit(0.125, d)
runit(0.175, d)
runit(1.0, d)
runit(-0.025, d)
runit(-0.125, d)
runit(-0.175, d)
runit(-1.0, d)

runit(0.0, 0)

a3144.release(a)



