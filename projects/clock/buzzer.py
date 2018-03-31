#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time

buzzerpin = 18 #GPIO18 pin is PWM for buzzer.
buzzerfreq = 1200
buzzerdutycycle = 75 #between 0-100 but 0 and 100 are silent.
beepfreq = 1.0

def run(  ):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(buzzerpin, GPIO.OUT)
    buzzer = GPIO.PWM(buzzerpin, buzzerfreq)

    phase = False

    while True:
      if phase:
        buzzer.stop()
      else:
        buzzer.start(buzzerdutycycle)

      phase = not phase
      time.sleep(beepfreq)

if __name__ == '__main__':  #start beeping.
  run()
  print('done')
