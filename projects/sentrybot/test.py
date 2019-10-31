#!/usr/bin/env python3

import RPi.GPIO as GPIO
from time import sleep
from buttons import gpioinit, button

gpioinit() #Initialize the GPIO system so we may use the pins for I/O.

pin = 20

GPIO.setup(pin, GPIO.OUT)
GPIO.output(pin, GPIO.HIGH)
print('on')
sleep(3.0)
GPIO.output(pin, GPIO.LOW)
print('off')
sleep(3.0)
GPIO.output(pin, GPIO.HIGH)
print('on')
sleep(3.0)
GPIO.output(pin, GPIO.LOW)
print('off')

