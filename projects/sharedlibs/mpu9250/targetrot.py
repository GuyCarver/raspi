#!/usr/bin/env python3

import math

class TargetRot(object):
  """Class to handle target rotation setting and checking"""

  _MAXROT = math.pi * 2.0
  _lrange = 1.0 / _MAXROT
  _hrange = 20.0 / _MAXROT

  def __init__(self):
    super(TargetRot, self).__init__()
    self._target = 0.0

  @property
  def target( self ):
    return self._target

  @target.setter
  def target( self, aValue ):
    self._target = aValue

  @classmethod
  def clamp( TargetRot, aRot ) :
    ''' Make sure the rotation is between 0 and _MAXROT. '''
    while aRot < 0.0:
      aRot += TargetRot._MAXROT

    return aRot % TargetRot._MAXROT

  def isbetween( self, aStart, aEnd, aValue ):
    '''  '''
    end = aEnd - aStart
    if end < 0.0:
      end += TargetRot._MAXROT

    mid = aValue - aStart
    if mid < 0.0:
      mid += TargetRot._MAXROT
    return (mid < end)

  def inrange( self, aValue, aDir ):
    if aDir < 0:
      low = TargetRot.clamp(self._target - TargetRot._hrange)
      high = TargetRot.clamp(self._target + TargetRot._lrange)
    else:
      low = TargetRot.clamp(self._target - TargetRot._lrange)
      high = TargetRot.clamp(self._target + TargetRot._hange)

    return self.isbetween(low, high, aValue)
