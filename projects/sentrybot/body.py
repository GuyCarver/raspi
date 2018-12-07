#!/usr/bin/env python3
#11/10/2018 11:10 AM

from quicrun import *
from atom import *

#------------------------------------------------------------------------
class part(object):
  '''abstract base for a body part.  anglepart and speedpart
     derive from this to control the value as either a +/-90 deg angle or
     0-100 speed.'''

  def __init__(self, aPCA, aIndex, aName):
    self._pca = aPCA
    self._index = aIndex
    self._name = aName
    self._value = -1.0
    self._currentValue = 0.0                    #The actual value that may vary from value if rate > 0.
    self._rate = 0.0                            #Rate of interpolation between _value and _target value.
                                                #This is in units/second.  IE: 180 is 180 degrees a second.
    self._minmax = self._defminmax
    self._center = 0.0
    self.value = 0.0                            #Set real value and write servo.
    self.scale = 1.0                            #Scale value

  @property
  def index( self ): return self._index

  @property
  def name( self ): return self._name

  @property
  def center( self ):
    return self._center

  @center.setter
  def center( self, aValue ):
    self._center = aValue

  @property
  def value( self ):
    return self._value

  @property
  def currentValue( self ):
    return self._currentValue

  @value.setter
  def value( self, aValue ):
    aValue = min(max(aValue, self._minmax[0] - self._center), self._minmax[1] - self._center)
    if aValue != self._value:
      self._value = aValue
      if self._rate <= 0.0:
        self._currentValue = aValue
        self.setservo()

  @property
  def minmax( self ):
    return self._minmax

  @minmax.setter
  def minmax( self, aValue ):
    #If tuple just use directly without checking legitimate ranges.
    if isinstance(aValue, tuple) or isinstance(aValue, list):
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

  def update( self, aDelta ):
    '''Update speed towards target given delta time in seconds.'''
    if self._rate > 0.0 and aDelta > 0.0:
      diff = self._value - self._currentValue
      if abs(diff) > 0.01:
        if diff < 0.0:
          mm = max
          d = -aDelta
        else:
          mm = min
          d = aDelta

        diff = mm(self._rate * d, diff)
        newvalue = self._currentValue + diff
        self._currentValue = mm(newvalue, self._value)
        self.setservo()

#------------------------------------------------------------------------
class anglepart(part):
  _defminmax = (-100.0, 100.0)

  '''Body part that uses an angle value from -90 to 90.'''
  def __init__( self, aPCA, aIndex, aName ):
    super(anglepart, self).__init__(aPCA, aIndex, aName)

  def setservo( self ):
    '''Set the servo to current angle.'''
    self._pca.setangle(self._index, int(self._currentValue + self._center))

#------------------------------------------------------------------------
class speedpart(part):
  _defminmax = (0.0, 100.0)

  '''Body part that uses a speed value from 0-100.'''
  def __init__( self, aPCA, aIndex, aName ):
    super(speedpart, self).__init__(aPCA, aIndex, aName)

  def setservo( self ):
    '''Set the servo to current speed.'''
    v = int(self._currentValue + self._center)
#    print('setting', v)
    self._pca.set(self._index, v)


#------------------------------------------------------------------------

_ANGLE, _SPEED, _MOTOR, _ATOM = range(4)

_CONSTRUCTORS = {_ANGLE : anglepart, _SPEED : speedpart, _MOTOR : quicrun, _ATOM : atom}

#Default data used to initialize the parts.  This will be
# modified by the json data.
#Name, Servo #, Type, Rate, Trim, Range (min, max) or minmax.
_defaultdata = (
 ("TORSO", 8, _ANGLE, 0.0, 0.0, 90.0),
 ("HEAD_H", 0, _ANGLE, 0.0, 0.0, 90.0),
 ("HEAD_V", 1, _ANGLE, 0.0, 0.0, 30.0),
 ("LARM_H", 2, _ANGLE, 0.0, 0.0, 90.0),
 ("LARM_V", 3, _ANGLE, 0.0, 0.0, 90.0),
 ("RARM_H", 5, _ANGLE, 0.0, 0.0, 90.0),
 ("RARM_V", 6, _ANGLE, 0.0, 0.0, 90.0),
 ("LLEG", 9, _MOTOR, 20.0, 0.0, 20.0),
 ("RLEG", 10, _MOTOR, 20.0, 0.0, 20.0),
 ("GUN", 11, _MOTOR, 25.0, 0.0, (0.0, 100.0)),
 ("MISSILES", 12, _ANGLE, 10.0, 0.0, 10.0),
 ("SMOKE", 15, _MOTOR, 1000.0, 0.0, (50.0, 100.0)),
)

_numparts = len(_defaultdata)

_TORSO, _HEAD_H, _HEAD_V, \
_LARM_H, _LARM_V, \
_RARM_H, _RARM_V, \
_LLEG, _RLEG, \
_GUN, _MISSILES, _SMOKE = range(_numparts)

_parts = [None] * _numparts

_initdata = None

def partindex( aName ):
  for i, v in enumerate(_defaultdata):
    if v[0] == aName:
      return i
  raise Exception("Part {} not found.".format(aName))

def getpart( aIndex ):
  return _parts[aIndex]

def parttype( aPart ):
  '''Get part type constructor enum from part type.'''
  tp = type(aPart)
  for t in _CONSTRUCTORS.items():
    if t[1] == tp:
      return t[0]

  raise Exception('Unknown part type {}.', tp)

def saveparts( aData ):
  '''Save part data for each part into the given json dictionary.'''
  def makeentry(i, p):
    return (_defaultdata[i][0], p.index, parttype(p), p.rate, p.center, p.minmaxforjson)

  data = [makeentry(i, p) for i, p in enumerate(_parts)]
  aData['parts'] = data

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
    name, index, typ, rate, center, minmax = pdata
    part = _CONSTRUCTORS[typ](aPCA, index, name)
    part.rate = rate
    part.minmax = minmax
    part.center = center
    part.value = center
    pi = partindex(name)
    _parts[pi]  = part

def setmotordata( aIndex, aRate, aMinMax ):
  '''Set the motor data on a part.'''
  _parts[aIndex].rate = aRate
  _parts[aIndex].minmax = aMinMax

def updateparts( aDelta ):
  '''Iterate through parts and call update.'''
  for p in _parts:
    p.update(aDelta)

def off( aIndex = -1 ):
  '''Turn given part off. If no part index given, turn all of them off.'''
  if aIndex >= 0:
    if _parts[aIndex]:
      _parts[aIndex].off()
  else:
    for p in _parts:
      if p:
        p.off()

from pca9865 import *

def test(  ):

  p = pca9865(100)
  sleep(2.0)
  a = anglepart(p, 5, 'test')
  a.minmax = 90.0
  a.rate = 90.0
  mn, mx = a.minmax

  def waitforit( part, aDir, aTarget ):
    a.value = aTarget
    while(part.currentValue != aTarget):
      print(part.currentValue, aTarget)
      sleep(0.01)
      part.update(0.01 * aDir)

  waitforit(a, 1.0, mx)
  waitforit(a, 1.0, mn)

  a.off()

  print('done')

#------------------------------------------------------------------------
if __name__ == '__main__': #Run tests.
  test()