#!/usr/bin/env python3

from quicrun import *

#------------------------------------------------------------------------
class part(object):
  '''abstract base for a body part.  anglepart and speedpart
     derive from this to control the value as either a +/-90 deg angle or
     0-100 speed.'''

  def __init__(self, aPCA, aIndex):
    self._pca = aPCA
    self._index = aIndex
    self._value = 1000.0                          #Stupid # to make sure 1st setting writes a value.
    self._rate = 0.0                              #Rate of interpolation between _value and _target value.
                                                  #This is in units/second.  IE: 180 is 180 degrees a second.
    self._minmax = self._defminmax
    self.value = 0.0                              #Set real value and write servo.

  @property
  def value( self ):
    return self._value

  @value.setter
  def value( self, aValue ):
    if aValue != self._value:
      self._value = aValue
      self.setservo()

  @property
  def minmax( self ):
    return self._minmax

  @minmax.setter
  def minmax( self, aValue ):
    #If tuple just use directly without checking legitimate ranges.
    if isinstance(aValue, tuple):
      self._minmax = aValue
    else:
      #otherwise it's considered a single # we use for both min/max.
      self._minmax = (max(-aValue, self._defminmax[0]), aValue)

  @property
  def minmaxforjson( self ):
    '''If min == -max then just return max (single value)
       otherwise return min/max tuple.'''
    if self._minmax[0] == -self._minmax[1]:
      return self._minmax[1]

    return self._minmax

  @property
  def rate( self ):
    return self._rate

  @rate.setter
  def rate( self, aValue ):
    self._rate = aValue

  def off( self ):
    '''Turn the servo off.'''
    self._pca.off(self._index)

  def clamp( self, aValue ):
    return min(max(aValue, self._minmax[0]), self._minmax[1])

  def update( self, aDelta ):
    '''Update speed towards target given delta time in seconds.'''
    if self._rate > 0.0:
      if aDelta != 0.0:
        diff = self.rate * aDelta
        self.value = self.clamp(self.value + diff)
    else:
      self.value = self.clamp(self.value)

#------------------------------------------------------------------------
class anglepart(part):
  '''Body part that uses an angle value from -90 to 90.'''
  def __init__( self, aPCA, aIndex ):
    self._defminmax = (-90.0, 90.0)
    super(anglepart, self).__init__(aPCA, aIndex)

  def setservo( self ):
    '''Set the servo to current angle.'''
    self._pca.setangle(self._index, int(self._value))

#------------------------------------------------------------------------
class speedpart(part):
  '''Body part that uses a speed value from 0-100.'''
  def __init__( self, aPCA, aIndex ):
    self._defminmax = (0.0, 100.0)
    super(speedpart, self).__init__(aPCA, aIndex)

  def setservo( self ):
    '''Set the servo to current speed.'''
    self._pca.set(self._index, int(self._value))

#------------------------------------------------------------------------

_ANGLE, _SPEED, _MOTOR = range(3)

_CONSTRUCTORS = {_ANGLE : anglepart, _SPEED : speedpart, _MOTOR : quicrun}

_partnames = [
  "TORSO",
  "HEAD_H",
  "HEAD_V",
  "LARM_H",
  "LARM_V",
  "RARM_H",
  "RARM_V",
  "LLEG",
  "RLEG",
  "GUN",
]

_numparts = len(_partnames)

_TORSO, _HEAD_H, _HEAD_V, \
_LARM_H, _LARM_V, _RARM_H, _RARM_V, \
_LLEG, _RLEG, _GUN = range(_numparts)

_parts = [None] * _numparts

#Default data used to initialize the parts.  This will be
# modified by the json data.
#Name, Servo #, Type, Rate, Range (min, max) or minmax.
_defaultdata = (
 ("TORSO", 1, _ANGLE, 90.0, 90.0),
 ("HEAD_H", 2, _ANGLE, 90.0, 90.0),
 ("HEAD_V", 3, _ANGLE, 90.0, 30.0),
 ("LARM_H", 4, _ANGLE, 90.0, 90.0),
 ("LARM_V", 5, _ANGLE, 90.0, 90.0),
 ("RARM_H", 6, _ANGLE, 90.0, 90.0),
 ("RARM_V", 7, _ANGLE, 90.0, 90.0),
 ("LLEG", 8, _MOTOR, 20.0, 20.0),
 ("RLEG", 9, _MOTOR, 20.0, 20.0),
 ("GUN", 10, _MOTOR, 75.0, 20.0),
)

_initdata = None

def getpart( aIndex ):
  return _parts[aIndex]

def parttype( aPart ):
  '''Get part type constructor enum from part type.'''
  tp = type(aPart)
  for t in _CONSTRUCTORS.items():
    if t[1] == tp:
      return t[0]

  raise Exception('Unknown part type {}.', tp)

def loadparts( aData ):
  '''Load data from given json dictionary.'''
  global _initdata

  try:
    _initdata = aData['parts']
  except:
    pass

def initparts( aPCA ):
  '''Initialize the parts from the _initdata dictionary.
      If that is None, use default data.'''
  global _initdata

  if _initdata == None:
    _initdata = _defaultdata

  #Create part for given part data.

  for pdata in _initdata:
    name, index, tp, rate, minmax = pdata
    pi = _partnames.index(name)
    part = _CONSTRUCTORS[tp](aPCA, index)
    part.rate = rate
    part.minmax = minmax
    _parts[pi]  = part

def saveparts( aData ):
  '''Save part data for each part into the given json dictionary.'''
  def makeentry(i, p):
    return (_partnames[i], p.index, parttype(p), p.rate, p.minmaxforjson)

  data = [makeentry(i, p) for i, p in enumerate(_parts)]
  aData['parts'] = data

def setmotordata( aIndex, aRate, aMinMax ):
  '''Set the motor data on a part.'''
  _parts[aIndex].rate = aRate
  _parts[aIndex].minmax = aMinMax

def off( aIndex = -1 ):
  '''Turn fiven part off. If no part index given, turn all of them off.'''
  if aIndex >= 0:
    _parts[aIndex].off()
  else:
    for p in _parts:
      p.off()

#------------------------------------------------------------------------
if __name__ == '__main__': #Run tests.
  from pca9865 import *

  p = pca9865()
  a = anglepart(p, 3)
  a.rate = 180.0
  mn, mx = a.minmax
  a.value = mn

  def waitforit( part, aDir, aTarget ):
    while(part.value != aTarget):
      sleep(0.01)
      part.update(0.01 * aDir)

  waitforit(a, 1.0, mx)
  waitforit(a, -1.0, mn)

  a.off()

  s = speedpart(p, 1)
  mn, mx = s.minmax
  s.rate = 75.0

  waitforit(s, 1.0, mx)
  waitforit(s, -1.0, mn)
  s.off()
  print('done')

