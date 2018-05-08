#!/usr/bin/env python3

# Controller for the quicrun 1060 Electronic Speed Control (ESP)
#This controller works through the pca9865 servo controller.

from time import sleep

#todo: May need to move speed values over time if the battery cannot handle it.

class quicrun(object):
  '''docstring for quicrun'''
  _STOP = 50
  _FORWARD_MAX = 68
  _FORWARD_MIN = 52
  _BACKWARD_MAX = 30
  _BACKWARD_MIN = 48
  _BACKWARD_INIT = 45

  @staticmethod
  def getperc( aMin, aMax, aPerc  ) :
    return (((aMax - aMin) * aPerc) // 100) + aMin

  def __init__(self, aPCA, aIndex):
    '''aPCA = pca9865 object to use for PWM control of the ESC.
       aIndex = Servo index on pca9865 (0-15).
    '''
    super(quicrun, self).__init__()
    self._pca = aPCA
    self._index = aIndex
    self.reset()

  def reset( self ) :
    self._pca.set(self._index, 75)
    sleep(0.5)
    self._pca.set(self._index, 100)
    sleep(0.5)
    self._pca.set(self._index, self._STOP)
    self._curspeed = 0

  def _set( self, aValue ) :
    self._pca.set(self._index, aValue)

  def _reverse( self ) :
    if self._currspeed >= 0 :
      self._set(self._STOP)
      sleep(0.1)
      self._set(self._BACKWARD_INIT)
      sleep(0.1)
      self._set(self._STOP)
      sleep(0.1)

  def speed( self, aSpeed ) :
    '''Set speed -100 to 100.'''
    aSpeed = max(min(100, aSpeed), -100)

    if aSpeed == 0 :
      self._set(self._STOP)
    else:
      if aSpeed > 0 :
        self._set(quicrun.getperc(self._FORWARD_MIN, self._FORWARD_MAX, aSpeed))
      else:
        self._reverse()
        self._set(quicrun.getperc(self._BACKWARD_MAX, self._BACKWARD_MIN, 100 + aSpeed))

    self._currspeed = aSpeed

