#!/usr/bin/env python3

import RPi.GPIO as GPIO
import pca
from time import perf_counter, sleep
from anim import anim
from math import fabs
from random import randint
import checkface
import keyboard

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

_dtime = .03

#------------------------------------------------------------------------
class mask(object):
  ''' Run the mask servo, LEDS and camera. '''

 #0.045 - 0.25
 #0.13 - 0.156

  _EYES = 0                                     # pca9865 eye servo index.
  LRED, RRED, RGREEN, RBLUE = range(4)          # LED animation indexes.
  _LEDINDEXES = [1, 2, 3, 4]                    # pca9865 LED indexes for the LEDs.
  _LEDMIN = 0.01                                # Minimum LED value.
  _LEDMAX = 1.0                                 # Maximum LED value.
  _LEDRANGE = _LEDMAX - _LEDMIN                 # Total range of led values.

  _EYEMIN = 18.0                                # Minimum eye value.
  _EYEMAX = 45.0                                # Maximum eye value.
  _EYERANGE = _EYEMAX - _EYEMIN                 # Total range of eye movement.
  _CENTER = _EYEMIN + (_EYERANGE / 2.0)         # Eye center value.
  _EYERATE = _EYERANGE / 2.0                    # Units per second to allow eye to change.
  _SWITCHDELAY = 3.0                            # Delay before we try to switch what face we are watching.
  _SEARCHDELAY = 30.0                           # Delay before we do a look l/r animation.
  _DOSNAP = False                               # Enable or Disable screen captures.
  _SNAPDELAY = 5.0                              # Time in seconds between screen captures if enabled.

  _looklr = ((_EYEMIN, 0.5), (_CENTER, 0.5), (_EYEMAX, 0.5), (_CENTER, 0.5))

#  _ud1 = ((_LEDMIN, 0.5), (_LEDMAX, 0.5), (0.0, 0.5))
#  _ud2 = ((_LEDMIN, 0.5), (_LEDMAX, 0.5), (0.0, 0.5))

#------------------------------------------------------------------------
  def __init__( self ):
    ''' Initialize the class and pca device. '''

    super(mask, self).__init__()

    self._eyeson = False

    pca.startup()
    self._camera = checkface.Create()
    self._snaptime = mask._SNAPDELAY
    self._initleds(0.0)

    checkface.SetVerticalFlip(self._camera, True)
#    checkface.SetScale(self._camera, 0.5)       # A smaller scale speeds up face detection but is less precise.

    self._anims = [anim(0.0, anim._DIRECT) for i in range(4)]
#    self._anims.append(anim(mask._ud1, anim._ONCE))
#    self._anims.append(anim(mask._ud1, anim._ONCE))

    self._eyeanim = anim(mask._looklr, anim._LOOP) # This animation is used to move eyes l/R during search state.
    self._eyestate = self.off
    self._switchtime = mask._SWITCHDELAY
    self._pos = mask._CENTER - 0.001            # Target position.
    self._curpos = mask._CENTER                 # Current eye position.
    self._faceindex = 0                         # Current face index if more than 1 face detected.
    self._maxwidth = 1.0                        # Width value to use for LED brightness scale.  Always set to maximum detected width.

    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

#------------------------------------------------------------------------
  def _initleds( self, aValue ):
    ''' Start LED animation. '''
    for i in range(len(mask._LEDINDEXES)):
      self.setled(i, aValue)

#------------------------------------------------------------------------
  def setled( self, aIndex, aValue ):
    ''' Set the led to the given float value 0.0-1.0 '''
    i = mask._LEDINDEXES[aIndex]
    pca.set(i, aValue)

#------------------------------------------------------------------------
  @property
  def eyeson( self ):
    return self._eyeson

  @eyeson.setter
  def eyeson( self, aValue ):
    self._eyeson = aValue
    if not aValue:
      pca.off(mask._EYES)                       # Turn servo off to save battery.

#------------------------------------------------------------------------
  @property
  def redeyes( self ):
    return self._anims[mask.LRED].value

  @redeyes.setter
  def redeyes( self, aValue ):
    ''' Set L/R red LEDS to given value. '''
#    print(aValue)
    self._anims[mask.LRED].value = aValue
    self._anims[mask.RRED].value = aValue

#------------------------------------------------------------------------
  def enteroff( self ):
    ''' Enter the off state.  Eye LEDs are off and eye servo is off. '''
    if self.eyeson:
      self.eyeson = False
    self._eyestate = self.off
    self.redeyes = 0.0
    self._switchtime = mask._SEARCHDELAY
#    print('\noff', end='')

#------------------------------------------------------------------------
  def off( self, dt ):
    ''' In off state look for faces and if one found exit off state. '''

    if checkface.Check(self._camera):
      self.enterswitch()
    else:
      #After a certain amount of time make the eyes look l/R with LEDs on.
      self._switchtime -= dt
      if self._switchtime <= 0:
        self.entersearch()

#------------------------------------------------------------------------
  def entertrack( self ):
    '''Enter the track state and follow the detected face.'''
    self._switchtime = mask._SWITCHDELAY
    self._eyestate = self.track
#    print('\ntrack')

#------------------------------------------------------------------------
  def track( self, dt ):
    #update eyes
    fs = checkface.FindFaces(self._camera)
    self._switchtime -= dt

    #If faces found.
    print('Faces: ', end = '')
    if fs:
      print(len(fs), ': ', end = '')
      self.eyeson = True
      #If our selected eye index is value then follow the face.
      if self._faceindex < len(fs):
        #Sort face rectangles by x.
        fs.sort(key=lambda a: a[0])
        x, y, w, h = fs[self._faceindex]
        print(x, y, w, h, '         ', end = '\r')
        center = x + (w // 2)
        perc = center / 360.0                   # Rectangle is within 0-320
        self._pos = (mask._EYERANGE * perc) + mask._EYEMIN
#         print(self._pos, '        ') #, end = '\r')

#        self._switchtime = mask._SWITCHDELAY
        if w > self._maxwidth:
          self._maxwidth = w

        self.redeyes = (min(1.0, w / self._maxwidth) * mask._LEDRANGE) + mask._LEDMIN
      else:
        self._switchtime = 0.0
        self.redeyes = 0.0

      if self._switchtime <= 0.0:
        self.enterswitch()
    else:
      print('0                       ', end = '\r')
      if self._switchtime <= 0.0:
        self.entercenter()

#------------------------------------------------------------------------
  def enterswitch( self ):
    ''' Attempt to pick a different face to watch. '''
    self._eyestate = self.switch
#    print('\nswitch', end='')

#------------------------------------------------------------------------
  def switch( self, dt ):
    fs = checkface.FindFaces(self._camera)
    if fs:
      self._faceindex = randint(0, len(fs) - 1)
      #Green = even index, #Blue = odd.
      i = (self._faceindex & 1)
      self._anims[i + mask.RGREEN].value = mask._LEDMIN
      self._anims[(1 - i) + mask.RGREEN].value = 0.0
#      self._anims[i].restart()
      self.entertrack()
    else:
      self.entercenter()                        #No face found so we'll just center eyes and turn off.

#------------------------------------------------------------------------
  def entercenter( self ):
    ''' Center the eyes then turn off. '''
    self.eyeson = True
    self._eyestate = self.center
    self._switchtime = 3.0                      #Give 1 second to do this.
    self._anims[mask.RGREEN].value = 0.0
    self._anims[mask.RBLUE].value = 0.0
    self._pos = mask._CENTER
#    print('\ncenter', end='')

#------------------------------------------------------------------------
  def center( self, dt ):
    ''' Move to center then turn off. '''
    #Todo: Maybe look for faces?

    self._switchtime -= dt
    if self._switchtime <= 0.0:
      self.enteroff()

#------------------------------------------------------------------------
  def entersearch( self ):
    ''' Play search animation. '''
    self._switchtime = 10.0
    self._eyestate = self.search
    self._eyeanim.restart()

#------------------------------------------------------------------------
  def search( self, dt ):
    ''' Perforce search animation (move eyes L/R) '''
    self._eyeanim.update(dt)
    self._pos = self._eyeanim.value
    self.redeyes = mask._LEDMIN
    self._anims[mask.RGREEN].value = mask._LEDMIN
    self._anims[mask.RBLUE].value = mask._LEDMIN

    # If we find a face then start tracking it.
    if checkface.Check(self._camera):
      self.enterswitch()
    else:
      print('search      ', end = '\r')
      # Loop til time is up or we ran the animation twice.
      self._switchtime -= dt
      if self._switchtime <= 0 or self._eyeanim.key == 8:
        self.entercenter()

#------------------------------------------------------------------------
  def update( self, dt ):
    ''' Update the eyes and LEDS. '''

    self._eyestate(dt)                          # Call eye state funcion.

    # Update the eye position.
    d = self._pos - self._curpos
    self._curpos += d * dt * mask._EYERATE
    if d < 0:
      if self._curpos < self._pos:
        self._curpos = self._pos
    elif self._curpos > self._pos:
      self._curpos = self._pos

    if mask._DOSNAP:
      self._snaptime -= dt
      if self._snaptime <= 0.0:
        self._snaptime = mask._SNAPDELAY
        checkface.SetCapture(self._camera)      # Next check will trigger a screen capture.

#     print(self._curpos)

    pca.setangle(mask._EYES, self._curpos)

    # update led intensity.
    for i, a in enumerate(self._anims):
      a.update(dt)
#      print(i, a.value)
      self.setled(i, a.value)

#------------------------------------------------------------------------
  def run( self ):
    ''' The main run loop. '''
    prevtime = perf_counter()

    while(True):
      if self._haskeyboard and keyboard.is_pressed('q'):
        break

      nexttime = perf_counter()
      delta = max(0.01, nexttime - prevtime)
      prevtime = nexttime
      if delta > _dtime:
#        print("Clamping delta: ", delta)
        delta = _dtime

      self.update(delta)

      nexttime = perf_counter()
      sleeptime = _dtime - (nexttime - prevtime)  # 30fps - time we've already wasted.
      if sleeptime > 0.0:
        sleep(sleeptime)

#------------------------------------------------------------------------
if __name__ == '__main__':
  m = mask()
  m.run()
