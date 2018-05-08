#!/usr/bin/env python3
#


from evdev import InputDevice, ecodes, list_devices
import os
from threading import Thread
from time import sleep

#def play1(  ):
#  os.system('mpg321 sounds/startup.mp3')
#
#def play2(  ):
#  os.system('mpg321 sounds/corrupt.mp3')

#t1 = Thread(target=play1)
#t2 = Thread(target=play2)
#t1.start()
#t2.start()

os.system('echo "power on \nconnect E4:17:D8:2C:08:68 \nquit" | sudo bluetoothctl')

#t1.join()
#t2.join()

sleep(1.0)
devices = [InputDevice(fn) for fn in list_devices()]
print(devices)
#for device in devices:
#  print(fn)
#  print(device.fn, device.name, device.phys)

for i in range(4):
  try:
    sleep(1.0)
    gamepad = InputDevice('/dev/input/event0')
    break
  except Exception as e:
    print(e)
    pass

#Button codes are as follows, type = 1 and val is 0 or 1 for buttons.
#types:
#EV_KEY = 1
#EV_ABS = 3
#
#a = 304 BTN_A
#b = 305 BTN_B
#x = 307 BTN_X
#y = 308 BTN_Y
#start = 315 BTN_START
#select = 314 BTN_SELECT
#rtrigger = 313 BTN_TR2
#ltrigger = 312 BTN_TL2
#rshoulder = 311 BTN_TR
#lshoulder = 310 BTN_TL
#lhat = 317 BTN_THUMBL
#rhat = 318 BTN_THUMBR
#
#dpadlr = 16, type = 3, val = -1 or 1 ABS_HAT0X
#dpadup = 17, type = 3, val = -1 or 1 ABS_HAT0Y
#
#rthumblr = 2, val = 0-255 ABS_Z
#rthumbud = 5, val = 0-255 ABS_RZ
#
#lthumblr = 0, type = 3, val = 0-255 255=right ABS_X
#lthumbud = 1, type = 3, val = 0-255 255=forward ABS_Y

#prints out device info at start
print(gamepad)
print(gamepad.capabilities(verbose=True))
print('leds:')
print(gamepad.leds(verbose=True))

def printbtn(value, btn):
  print(btn + (' pressed' if value else ' released'))

#loop and filter by event code and print the mapped label
for event in gamepad.read_loop():
  if event.type == ecodes.EV_KEY:
    if event.code == ecodes.BTN_A:
      printbtn(event.value, 'A')
    if event.code == ecodes.BTN_B:
      printbtn(event.value, 'B')
    if event.code == ecodes.BTN_X:
      printbtn(event.value, 'B')
    if event.code == ecodes.BTN_Y:
      printbtn(event.value, 'Y')
    if event.code == ecodes.BTN_START:
      printbtn(event.value, 'START')
    if event.code == ecodes.BTN_SELECT:
      printbtn(event.value, 'SELECT')
    if event.code == ecodes.BTN_TR2:
      printbtn(event.value, 'rtrigger')
    if event.code == ecodes.BTN_TL2:
      printbtn(event.value, 'ltrigger')
    if event.code == ecodes.BTN_TR:
      printbtn(event.value, 'rshoulder')
    if event.code == ecodes.BTN_TL:
      printbtn(event.value, 'lshoulder')
    if event.code == ecodes.BTN_THUMBL:
      printbtn(event.value, 'lhat')
    if event.code == ecodes.BTN_THUMBR:
      printbtn(event.value, 'rhat')
  elif event.type == ecodes.EV_ABS:
    pass
#    if event.type == ecodes.EV_KEY:
#        if event.value == 1:
#            if event.code == yBtn:
#                print("Y")
#            elif event.code == bBtn:
#                print("B")
#            elif event.code == aBtn:
#                print("A")
#            elif event.code == xBtn:
#                print("X")
#
#            elif event.code == up:
#                print("up")
#            elif event.code == down:
#                print("down")
#            elif event.code == left:
#                print("left")
#            elif event.code == right:
#                print("right")
#
#            elif event.code == start:
#                print("start")
#            elif event.code == select:
#                print("select")
#
#            elif event.code == lTrig:
#                print("left bumper")
#            elif event.code == rTrig:
#                print("right bumper")
