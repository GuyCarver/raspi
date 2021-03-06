#!/usr/bin/env python3

#todo: Handle hal sensor use for tracking range

class arm(object):
  ''' Arm servo control. Takes minimum, maximum and center angle
       values for the servo controller and manages setting from
       a value of -1.0 to 1.0 '''

  #--------------------------------------------------------
  def __init__( self, aPCA, aIndex, aRate, aRange ):
    ''' aPCA = pca9685, pin index for pca, rate in range/second and tuple of ranges (min, center, max). '''

    super(arm, self).__init__()
    self._pca = aPCA
    self._index = aIndex
    self._range = aRange
    self._rate = aRate
    self.angle = 0.0  #Set to center

  #--------------------------------------------------------
  @property
  def angle( self ):
    return self._angle

  #--------------------------------------------------------
  @angle.setter
  def angle( self, aValue ):
    ''' Set angle to given percentage -1.0 to 1.0. '''
    self._angle = max(min(1.0, aValue), -1.0)

    if self._angle < 0.0:
      r = self._range[1] - self._range[0]
    else:
      r = self._range[2] - self._range[1]

    v = r * self._angle + self._range[1]

#     print(self._value, v)
    self._pca.setangle(self._index, v)

  #--------------------------------------------------------
  def update( self, aDelta ):
    ''' Update value based on aDelta * _rate. '''
    self.angle += (aDelta * self._rate)

#--------------------------------------------------------
class extension(object):
  ''' Arm extension continuous rotation servo.'''

  #--------------------------------------------------------
  def __init__( self, aPCA, aIndex, aRange ):
    ''' aPCA = pca9685, pin index for pca, rate in range/second and tuple of ranges (min, center, max). '''

    super(extension, self).__init__()
    self._pca = aPCA
    self._index = aIndex
    self._range = aRange
    self.speed = 0.0                            # Set to center

  #--------------------------------------------------------
  @property
  def speed( self ):
    return self._speed

  #--------------------------------------------------------
  @speed.setter
  def speed( self, aValue ):
    ''' Set speed to given percentage -1.0 to 1.0. '''

    self._speed = max(min(1.0, aValue), -1.0)

    if self._speed < 0.0:
      r = self._range[1] - self._range[0]
    else:
      r = self._range[2] - self._range[1]

    v = r * self._speed + self._range[1]

    self._pca.set(self._index, v)
